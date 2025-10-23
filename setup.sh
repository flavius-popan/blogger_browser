#!/bin/bash

################################################################################
# Blog Authorship Corpus Setup Script
################################################################################
#
# This script automates the complete setup process for the journal_hunt project:
#   1. Downloads the Blog Authorship Corpus from HuggingFace
#   2. Extracts the dataset
#   3. Filters journals by file size (configurable)
#   4. Checks and installs dependencies (fzf)
#   5. Runs analysis to generate metrics
#   6. Launches the interactive reader
#
# USAGE:
#   ./setup_browser.sh                   # Run normal setup
#   ./setup_browser.sh --force           # Force re-analysis even if CSV exists
#   ./setup_browser.sh --keep-source     # Keep blogs.zip and blogs/ after filtering
#   ./setup_browser.sh --help            # Show help message
#
# IDEMPOTENT: Safe to run multiple times. Steps are skipped if already completed.
#
################################################################################

set -e # Exit on error

################################################################################
# CONFIGURATION - Modify these values to adjust filtering behavior
################################################################################

# Minimum file size for journals (passed to `find -size` command)
# Examples: 100k, 200k, 1M, 500k
# The dataset has ~19,320 files; >100k yields ~1,700 files
MIN_FILE_SIZE="100k"

# Minimum entries threshold (used by analyze_blogs.py at line 231)
# Journals with fewer entries are excluded from the CSV
# Note: This is enforced by analyze_blogs.py, not this script
MIN_ENTRIES=30

# Dataset download URL
DATASET_URL="https://huggingface.co/datasets/barilan/blog_authorship_corpus/resolve/main/data/blogs.zip?download=true"

# Directories
DOWNLOAD_DIR="."
EXTRACT_DIR="blogs"
DATA_DIR="data"
OUTPUT_CSV="journal_analysis.csv"

################################################################################
# COLOR OUTPUT
################################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

success() {
  echo -e "${GREEN}✓${NC} $1"
}

warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

error() {
  echo -e "${RED}✗${NC} $1"
}

################################################################################
# HELP MESSAGE
################################################################################

show_help() {
  cat <<EOF
Blog Authorship Corpus Setup Script

USAGE:
    ./setup_browser.sh [OPTIONS]

OPTIONS:
    --force         Force re-analysis even if CSV already exists
    --keep-source   Keep blogs.zip and blogs/ directory (auto-deleted by default)
    --help          Show this help message

CONFIGURATION:
    Edit the configuration section at the top of this script to modify:
    - MIN_FILE_SIZE: Minimum journal file size (default: ${MIN_FILE_SIZE})
    - MIN_ENTRIES: Minimum entries per journal (default: ${MIN_ENTRIES})

EXAMPLES:
    ./setup_browser.sh                    # Run normal setup (auto-cleanup)
    ./setup_browser.sh --force            # Force re-run of analysis
    ./setup_browser.sh --keep-source      # Preserve original dataset files

    # To change file size threshold, edit MIN_FILE_SIZE in this script
    # Then re-run after clearing data directory:
    rm -rf data/* && ./setup_browser.sh

EOF
}

################################################################################
# ARGUMENT PARSING
################################################################################

FORCE_ANALYSIS=false
KEEP_SOURCE=false

while [[ $# -gt 0 ]]; do
  case $1 in
  --force)
    FORCE_ANALYSIS=true
    shift
    ;;
  --keep-source)
    KEEP_SOURCE=true
    shift
    ;;
  --help | -h)
    show_help
    exit 0
    ;;
  *)
    error "Unknown option: $1"
    echo "Run './setup_browser.sh --help' for usage information"
    exit 1
    ;;
  esac
done

################################################################################
# DEPENDENCY CHECKS
################################################################################

check_dependencies() {
  info "Checking dependencies..."

  # Check for Python 3
  if ! command -v python3 &>/dev/null; then
    error "python3 is not installed. Please install Python 3 and try again."
    exit 1
  fi
  success "Python 3 found: $(python3 --version)"

  # Check for curl (needed for download)
  if ! command -v curl &>/dev/null; then
    error "curl is not installed. Please install curl and try again."
    exit 1
  fi

  # Check for unzip
  if ! command -v unzip &>/dev/null; then
    error "unzip is not installed. Please install unzip and try again."
    exit 1
  fi

  # Check for fzf
  if ! command -v fzf &>/dev/null; then
    warning "fzf is not installed. It's required to run the interactive reader."

    # Check if Homebrew is available
    if ! command -v brew &>/dev/null; then
      error "Homebrew is not installed."
      echo ""
      echo "To install Homebrew, visit: https://brew.sh"
      echo "Or run: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
      echo ""
      echo "After installing Homebrew, run: brew install fzf"
      exit 1
    fi

    # Offer to install fzf
    echo ""
    read -p "Would you like to install fzf now using Homebrew? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      info "Installing fzf via Homebrew..."
      brew install fzf
      success "fzf installed successfully"
    else
      warning "Skipping fzf installation. You can install it later with: brew install fzf"
      echo "Setup will continue, but you won't be able to run the reader until fzf is installed."
      echo ""
      read -p "Press Enter to continue or Ctrl+C to abort..."
    fi
  else
    success "fzf found"
  fi
}

################################################################################
# DATASET DOWNLOAD
################################################################################

download_dataset() {
  local zip_file="${DOWNLOAD_DIR}/blogs.zip"

  if [ -f "$zip_file" ]; then
    success "blogs.zip already exists, skipping download"
    return 0
  fi

  info "Downloading Blog Authorship Corpus from HuggingFace (~300MB)..."
  echo ""

  if curl -L -o "$zip_file" "$DATASET_URL" --progress-bar; then
    echo ""
    success "Download complete: $zip_file"
  else
    error "Download failed. Please check your internet connection and try again."
    exit 1
  fi
}

################################################################################
# DATASET EXTRACTION
################################################################################

extract_dataset() {
  local zip_file="${DOWNLOAD_DIR}/blogs.zip"

  if [ -d "$EXTRACT_DIR" ]; then
    success "$EXTRACT_DIR directory already exists, skipping extraction"
    return 0
  fi

  if [ ! -f "$zip_file" ]; then
    error "blogs.zip not found. Cannot extract."
    exit 1
  fi

  info "Extracting blogs.zip..."

  if unzip -q "$zip_file" -d "$DOWNLOAD_DIR"; then
    success "Extraction complete: $EXTRACT_DIR/"
  else
    error "Extraction failed"
    exit 1
  fi
}

################################################################################
# FILE FILTERING
################################################################################

filter_files() {
  # Create data directory if it doesn't exist
  mkdir -p "$DATA_DIR"

  # Check if files already exist in data/
  local existing_count=$(find "$DATA_DIR" -name "*.xml" 2>/dev/null | wc -l | tr -d ' ')

  if [ "$existing_count" -gt 0 ]; then
    success "$DATA_DIR already contains $existing_count XML files, skipping filtering"
    info "To re-filter with different criteria, run: rm -rf $DATA_DIR/* && ./setup_browser.sh"
    return 0
  fi

  if [ ! -d "$EXTRACT_DIR" ]; then
    error "$EXTRACT_DIR directory not found. Cannot filter files."
    exit 1
  fi

  info "Filtering journals larger than ${MIN_FILE_SIZE}..."

  # Count total files before filtering
  local total_files=$(find "$EXTRACT_DIR" -name "*.xml" 2>/dev/null | wc -l | tr -d ' ')

  # Copy files larger than MIN_FILE_SIZE (quietly)
  find "$EXTRACT_DIR" -name "*.xml" -size "+${MIN_FILE_SIZE}" -exec cp {} "$DATA_DIR/" \; 2>/dev/null

  local filtered_count=$(find "$DATA_DIR" -name "*.xml" 2>/dev/null | wc -l | tr -d ' ')

  # Calculate percentage
  local percentage=0
  if [ "$total_files" -gt 0 ]; then
    percentage=$((filtered_count * 100 / total_files))
  fi

  success "Copied $filtered_count of $total_files files (${percentage}%, >${MIN_FILE_SIZE}) to $DATA_DIR/"
  sleep 1
}

################################################################################
# CLEANUP
################################################################################

cleanup_original_data() {
  local zip_file="${DOWNLOAD_DIR}/blogs.zip"

  if [ ! -d "$EXTRACT_DIR" ] && [ ! -f "$zip_file" ]; then
    # Already cleaned up
    return 0
  fi

  if [ "$KEEP_SOURCE" = true ]; then
    info "Keeping source files (blogs.zip and $EXTRACT_DIR directory)"
    return 0
  fi

  info "Cleaning up source files (~2GB)..."

  rm -rf "$EXTRACT_DIR" 2>/dev/null
  rm -f "$zip_file" 2>/dev/null

  success "Removed blogs.zip and $EXTRACT_DIR directory"
}

################################################################################
# ANALYSIS
################################################################################

run_analysis() {
  if [ -f "$OUTPUT_CSV" ] && [ "$FORCE_ANALYSIS" = false ]; then
    success "$OUTPUT_CSV already exists, skipping analysis"
    info "To force re-analysis, run: ./setup_browser.sh --force"
    return 0
  fi

  if [ ! -f "analyze_blogs.py" ]; then
    error "analyze_blogs.py not found in current directory"
    exit 1
  fi

  local file_count=$(find "$DATA_DIR" -name "*.xml" 2>/dev/null | wc -l | tr -d ' ')

  if [ "$file_count" -eq 0 ]; then
    error "No XML files found in $DATA_DIR/"
    exit 1
  fi

  info "Running analysis on $file_count journal files (filtering to ${MIN_ENTRIES}+ entries)..."
  echo ""

  if python3 analyze_blogs.py; then
    echo ""
  else
    error "Analysis failed"
    exit 1
  fi
}

################################################################################
# READER
################################################################################

start_reader() {
  if [ ! -f "reader.py" ]; then
    error "reader.py not found in current directory"
    exit 1
  fi

  if [ ! -f "$OUTPUT_CSV" ]; then
    error "$OUTPUT_CSV not found. Run analysis first."
    exit 1
  fi

  # Check for fzf again before starting reader
  if ! command -v fzf &>/dev/null; then
    echo ""
    warning "fzf is not installed. Cannot start interactive reader."
    info "Install fzf with: brew install fzf"
    info "Then run: python3 reader.py"
    echo ""
    exit 0
  fi

  echo ""
  echo "=========================================="
  success "Setup complete!"
  echo "=========================================="
  echo ""
  info "The journal reader is ready to launch."
  info "From now on, simply run: ${GREEN}python3 reader.py${NC}"
  info "(No need to re-run this setup script)"
  echo ""
  read -n 1 -s -r -p "Press any key to launch reader..."
  echo ""
  echo ""

  python3 reader.py
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
  echo ""
  echo "=========================================="
  echo "  Blog Authorship Corpus Setup"
  echo "=========================================="
  echo ""

  check_dependencies
  download_dataset
  extract_dataset
  filter_files
  cleanup_original_data
  run_analysis
  start_reader
}

# Run main function
main
