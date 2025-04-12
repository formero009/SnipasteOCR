#!/bin/bash
# Shell script for building SnipasteOCR on Linux

# Function to clean build artifacts
clean_build_files() {
    echo "Cleaning old build files..."
    if [ -d "build" ]; then rm -rf build; fi
    if [ -d "dist" ]; then rm -rf dist; fi
    if ls *.spec 1> /dev/null 2>&1; then rm -f *.spec; fi
}

# Main menu loop
while true; do
    clear
    echo "================================"
    echo "     SnipasteOCR Builder (Linux)"
    echo "================================"
    echo "1. Debug Build (with console)"
    echo "2. Release Build (no console)"
    echo "3. Clean Build Files"
    echo "4. Exit"
    echo "================================"
    echo ""

    read -p "Select an option (1-4): " choice

    case $choice in
        1)
            # Debug Build
            clean_build_files
            echo "Building Debug version..."
            uv run pyinstaller -c main.py \
                --collect-all fastdeploy \
                --name=SnipasteOCR \
                --icon=assets/icon.ico \
                --add-data="models:models" \
                --add-data="assets:assets" \
                --add-data="config.yml:." \
                --hidden-import=pyqt6 \
                --hidden-import=PyQt6.QtWidgets \
                --hidden-import=PyQt6.QtGui \
                --hidden-import=PyQt6.QtCore \
                --hidden-import=PyQt6.sip \
                --clean \
                --noconfirm

            if [ $? -ne 0 ]; then
                echo "Build failed! Check the error message."
                read -p "Press Enter to continue..."
            else
                echo ""
                echo "Build completed!"
                echo "Output directory: dist/SnipasteOCR/"
                echo "Executable: dist/SnipasteOCR/SnipasteOCR"
                read -p "Press Enter to continue..."
            fi
            ;;
        2)
            # Release Build
            clean_build_files
            echo "Building Release version..."
            uv run pyinstaller -w main.py \
                --collect-all fastdeploy \
                --name=SnipasteOCR \
                --icon=assets/icon.ico \
                --add-data="models:models" \
                --add-data="assets:assets" \
                --add-data="config.yml:." \
                --hidden-import=pyqt6 \
                --hidden-import=PyQt6.QtWidgets \
                --hidden-import=PyQt6.QtGui \
                --hidden-import=PyQt6.QtCore \
                --hidden-import=PyQt6.sip \
                --clean \
                --noconfirm

            if [ $? -ne 0 ]; then
                echo "Build failed! Check the error message."
                read -p "Press Enter to continue..."
            else
                echo ""
                echo "Build completed!"
                echo "Output directory: dist/SnipasteOCR/"
                echo "Executable: dist/SnipasteOCR/SnipasteOCR"
                read -p "Press Enter to continue..."
            fi
            ;;
        3)
            # Clean
            echo "Cleaning build files..."
            if [ -d "build" ]; then rm -rf build; fi
            if [ -d "dist" ]; then rm -rf dist; fi
            if ls *.spec 1> /dev/null 2>&1; then rm -f *.spec; fi
            echo "Done!"
            read -p "Press Enter to continue..."
            ;;
        4)
            # Exit
            exit 0
            ;;
        *)
            # Invalid choice
            echo "Invalid option. Please select 1-4."
            read -p "Press Enter to continue..."
            ;;
    esac
done 