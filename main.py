import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.viewer import DiffViewer

def main():
    # Set paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(current_dir, "results_to_compare")
    # results_dir = "D:/Projects/DV/test/results_to_compare"
    template_dir = os.path.join(current_dir, "src", "templates")
    static_dir = os.path.join(current_dir, "static")

    print(f"Current directory: {current_dir}")
    print(f"Results directory: {results_dir}")
    print(f"Template directory: {template_dir}")
    print(f"Static directory: {static_dir}")
    print(f"Database will be at: {os.path.join(current_dir, 'progress.db')}")


    if not os.path.exists(results_dir):
        print(f"Results directory not found: {results_dir}")
        print("Please create the directory and add your API result files.")
        return
    
    # Initialize and run viewer
    viewer = DiffViewer(
        results_dir=results_dir,
        template_dir=os.path.join(os.path.dirname(__file__), 'src', 'templates'),
        static_dir=os.path.join(os.path.dirname(__file__), 'static')
    )
    
    # Run the application
    viewer.run(host='127.0.0.1', port=5000, debug=True)

if __name__ == "__main__":
    main()