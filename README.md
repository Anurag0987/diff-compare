# API Diff Viewer

A powerful web-based tool for comparing API responses side-by-side with visual difference highlighting, progress tracking, and resolution management.

## 🚀 Features

### Core Functionality
- **Side-by-Side JSON Comparison**: Visual diff viewer with line-by-line comparison
- **Real-time Difference Highlighting**: Automatic detection and highlighting of JSON differences
- **Interactive Navigation**: Click to jump to specific differences in large files
- **Synchronized Scrolling**: Both panels scroll together for easy comparison

### Progress Management
- **Persistent Progress Tracking**: Your work is automatically saved to a local SQLite database
- **Flag System**: Mark files with priority levels (High, Medium, Low)
- **Comments**: Add notes and observations for each file comparison
- **Resolution Tracking**: Mark entire files or individual differences as resolved
- **Visual Status Indicators**: Color-coded folder and file states

### User Experience
- **Responsive Design**: Works on desktop and tablet devices
- **Folder Organization**: Automatically groups files by domain/category
- **Search & Filter**: Quickly find specific files or differences
- **Export Capabilities**: Save your progress and analysis results
- **Session Management**: Resume work exactly where you left off

## 📁 Required Directory Structure

Your `results_to_compare` directory should follow this structure:


```
results_to_compare/
├── Folder1/ <-- Tab Group Name on UI (grouped by this folder name on UI)
│   ├── Response1.json <-- JSON1 file with below structure to compare
│   ├── Response2.json  <-- JSON2 file with below structure to compare
├── Folder1/ 
│   ├── Response1.json
│   ├── Response2.json
├── Folder2/
│   ├── Response1.json
│   └── Response2.json
└── ...
```

### JSON Response File Format

Each response file should contain a JSON object with this structure:

```json
{
  "response_data": { // <-- mian data to display on UI
    // Your actual API response data goes here
    "status": "success",
    "data": [...],
    "metadata": {...}
  },
  "timestamp": "2024-01-15T10:30:00Z", // <-- Optional
  "api_endpoint": "/api/v1/endpoint", // <-- Optional
  "response_time_ms": 245 // <-- Optional
}
```

The tool will extract and compare the `response_data` section from each file.

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Quick Start

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd api-diff-viewer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your data**
   - Create an `results_to_compare` folder in the project root
   - Organize your JSON response files following the structure above
   - Ensure each folder has at least 2 response files for comparison

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Open your browser**
   - Navigate to `http://localhost:5000`
   - Start comparing your API responses!

## 📊 Usage Guide

### Basic Workflow

1. **Select a File**: Click on any file in the sidebar to load the comparison
2. **Review Differences**: 
   - Differences are highlighted in red
   - Use "Show Differences" to see a detailed list
   - Click "Show" next to any difference to jump to that line
3. **Track Progress**:
   - Set a priority flag (High/Medium/Low)
   - Add comments about your findings
   - Mark individual differences as resolved
   - Mark the entire comparison as resolved when done

### Keyboard Shortcuts
- `Ctrl + F`: Search within the current diff
- `↑/↓ Arrow Keys`: Navigate through differences
- `Escape`: Close difference panel

### Visual Indicators

| Color | Meaning |
|-------|---------|
| 🔴 Red | Unresolved differences |
| 🟢 Green | Resolved differences |
| 🟡 Yellow | High priority |
| 🟠 Orange | Medium priority |
| 🔵 Blue | Low priority |

## 🗃️ Data Persistence

All your progress is automatically saved to a local SQLite database (`progress.db`):

- **Flags & Comments**: Persist across sessions
- **Resolved States**: Individual and file-level resolution tracking
- **Session History**: Resume work exactly where you left off
- **Export Options**: Backup your analysis results

## 📋 Example Use Cases

### API Migration Testing
Compare responses between old and new API versions to ensure compatibility:
```
migration_test/
├── UserAPI_GetProfile_v1_vs_v2/
├── PaymentAPI_ProcessPayment_v1_vs_v2/
└── AuthAPI_Login_v1_vs_v2/
```

### Environment Comparison
Compare API responses across different environments:
```
environment_comparison/
├── ProductAPI_GetCatalog_prod_vs_staging/
├── UserAPI_GetProfile_prod_vs_dev/
└── OrderAPI_CreateOrder_prod_vs_test/
```

### A/B Testing Analysis
Compare different API implementations:
```
ab_testing/
├── RecommendationAPI_Algorithm_A_vs_B/
├── SearchAPI_Ranking_V1_vs_V2/
└── PaymentAPI_Gateway_Stripe_vs_PayPal/
```

## 🔧 Configuration

### Custom Ignore Patterns
Edit `src/file_processor.py` to ignore specific JSON paths:

```python
self.ignore_patterns = [
    r'data\[\d+\]\.timestamp',    # Ignore timestamps
    r'metadata\.request_id',       # Ignore request IDs
    r'response_time_ms'            # Ignore response times
]
```

### Database Location
By default, `progress.db` is created in the project root. To change this, modify `src/storage_manager.py`.

## 🎯 Advanced Features

### Bulk Operations
- Mark multiple files as resolved
- Export progress reports
- Batch flag assignments

### Integration Options
- REST API endpoints for external integration
- Export results to CSV/JSON
- Command-line interface for automation

## 🐛 Troubleshooting

### Common Issues

**"No files found"**
- Verify your `results_to_compare` directory structure
- Check that folders contain at least 2 response files

**"Failed to load differences"**
- Verify JSON files are valid
- Check file permissions
- Ensure response files contain `response_data` key

**"Progress not saving"**
- Check database permissions
- Verify `progress.db` is writable
- Restart the application

### Debug Mode
Run with debug enabled for detailed logging:
```bash
python main.py --debug
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions, issues, or feature requests:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the example directory structures

---

**Happy API Diffing! 🚀**