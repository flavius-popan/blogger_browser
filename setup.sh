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
#   ./setup.sh              # Run normal setup
#   ./setup.sh --force      # Force re-analysis even if CSV exists
#   ./setup.sh --help       # Show help message
#
# IDEMPOTENT: Safe to run multiple times. Steps are skipped if already completed.
#
################################################################################

set -e  # Exit on error

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
    cat << EOF
Blog Authorship Corpus Setup Script

USAGE:
    ./setup.sh [OPTIONS]

OPTIONS:
    --force         Force re-analysis even if CSV already exists
    --help          Show this help message

CONFIGURATION:
    Edit the configuration section at the top of this script to modify:
    - MIN_FILE_SIZE: Minimum journal file size (default: ${MIN_FILE_SIZE})
    - MIN_ENTRIES: Minimum entries per journal (default: ${MIN_ENTRIES})

EXAMPLES:
    ./setup.sh                    # Run normal setup
    ./setup.sh --force            # Force re-run of analysis

    # To change file size threshold, edit MIN_FILE_SIZE in this script
    # Then re-run after clearing data directory:
    rm -rf data/* && ./setup.sh

EOF
}

################################################################################
# ARGUMENT PARSING
################################################################################

FORCE_ANALYSIS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_ANALYSIS=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Run './setup.sh --help' for usage information"
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
    if ! command -v python3 &> /dev/null; then
        error "python3 is not installed. Please install Python 3 and try again."
        exit 1
    fi
    success "Python 3 found: $(python3 --version)"

    # Check for curl (needed for download)
    if ! command -v curl &> /dev/null; then
        error "curl is not installed. Please install curl and try again."
        exit 1
    fi

    # Check for unzip
    if ! command -v unzip &> /dev/null; then
        error "unzip is not installed. Please install unzip and try again."
        exit 1
    fi

    # Check for fzf
    if ! command -v fzf &> /dev/null; then
        warning "fzf is not installed. It's required to run the interactive reader."

        # Check if Homebrew is available
        if ! command -v brew &> /dev/null; then
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

    info "Preparing to download Blog Authorship Corpus (~300MB)..."
    echo ""
    read -p "Download dataset from HuggingFace? (y/n) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warning "Download cancelled. Exiting."
        exit 0
    fi

    info "Downloading blogs.zip from HuggingFace..."
    info "This may take a few minutes depending on your connection..."

    if curl -L -o "$zip_file" "$DATASET_URL" --progress-bar; then
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
        info "To re-filter with different criteria, run: rm -rf $DATA_DIR/* && ./setup.sh"
        return 0
    fi

    if [ ! -d "$EXTRACT_DIR" ]; then
        error "$EXTRACT_DIR directory not found. Cannot filter files."
        exit 1
    fi

    info "Filtering journals larger than ${MIN_FILE_SIZE}..."
    info "This will copy files from $EXTRACT_DIR/ to $DATA_DIR/"

    # Count total files before filtering
    local total_files=$(find "$EXTRACT_DIR" -name "*.xml" | wc -l | tr -d ' ')
    info "Total XML files in dataset: $total_files"

    # Copy files larger than MIN_FILE_SIZE
    find "$EXTRACT_DIR" -name "*.xml" -size "+${MIN_FILE_SIZE}" -exec cp {} "$DATA_DIR/" \;

    local filtered_count=$(find "$DATA_DIR" -name "*.xml" | wc -l | tr -d ' ')
    success "Filtered $filtered_count files (>${MIN_FILE_SIZE}) to $DATA_DIR/"

    # Calculate percentage
    if [ "$total_files" -gt 0 ]; then
        local percentage=$((filtered_count * 100 / total_files))
        info "Selected ${percentage}% of total files"
    fi
}

################################################################################
# CLEANUP
################################################################################

cleanup_original_data() {
    local zip_file="${DOWNLOAD_DIR}/blogs.zip"

    if [ ! -d "$EXTRACT_DIR" ]; then
        # Already cleaned up
        return 0
    fi

    echo ""
    info "The original $EXTRACT_DIR directory contains all 19,320 blog files."
    info "You can safely delete it to save disk space (~2GB)."
    echo ""
    read -p "Delete $EXTRACT_DIR directory and blogs.zip? (y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Removing $EXTRACT_DIR..."
        rm -rf "$EXTRACT_DIR"

        if [ -f "$zip_file" ]; then
            info "Removing $zip_file..."
            rm -f "$zip_file"
        fi

        success "Cleanup complete"
    else
        info "Keeping $EXTRACT_DIR and $zip_file"
    fi
}

################################################################################
# ANALYSIS
################################################################################

run_analysis() {
    if [ -f "$OUTPUT_CSV" ] && [ "$FORCE_ANALYSIS" = false ]; then
        success "$OUTPUT_CSV already exists, skipping analysis"
        info "To force re-analysis, run: ./setup.sh --force"
        return 0
    fi

    if [ ! -f "analyze_blogs.py" ]; then
        error "analyze_blogs.py not found in current directory"
        exit 1
    fi

    local file_count=$(find "$DATA_DIR" -name "*.xml" | wc -l | tr -d ' ')

    if [ "$file_count" -eq 0 ]; then
        error "No XML files found in $DATA_DIR/"
        exit 1
    fi

    info "Running analysis on $file_count journal files..."
    info "Journals with <${MIN_ENTRIES} entries will be filtered out by analyze_blogs.py"

    if python3 analyze_blogs.py; then
        success "Analysis complete: $OUTPUT_CSV"
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
    if ! command -v fzf &> /dev/null; then
        warning "fzf is not installed. Cannot start interactive reader."
        info "Install fzf with: brew install fzf"
        info "Then run: python3 reader.py"
        exit 0
    fi

    echo ""
    success "Setup complete! Starting interactive journal reader..."
    info "Press 'q' to exit the reader"
    echo ""
    sleep 1

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
    echo "Configuration:"
    echo "  • Min file size: ${MIN_FILE_SIZE}"
    echo "  • Min entries: ${MIN_ENTRIES}"
    echo "  • Data directory: ${DATA_DIR}"
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
