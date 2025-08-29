import os
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from file_processor import FileProcessor
from storage_manager import StorageManager

class DiffViewer:
    def __init__(self, results_dir, template_dir="templates", static_dir="static"):
        self.results_dir = results_dir
        self.template_dir = template_dir
        self.static_dir = static_dir
        self.file_processor = FileProcessor(results_dir)
        self.storage_manager = StorageManager(results_dir)

        print(f"Viewer initialized with:")
        print(f"  Results dir: {results_dir}")
        print(f"  Database path: {self.storage_manager.db_path}")
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder=template_dir,
                        static_folder=static_dir)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main viewer page"""
            try:
                # Get file structure and convert to folder_groups format expected by template
                file_structure = self.file_processor.get_file_structure()
                
                # Convert file_structure to folder_groups format for template compatibility
                folder_groups = {}
                for main_folder, files in file_structure.items():
                    folder_groups[main_folder] = []
                    for file_info in files:
                        folder_groups[main_folder].append({
                            'folder_name': file_info['folder_name'],
                            'sub_filename': file_info['sub_filename'],
                            'file_path': file_info['file_path'],
                            'comparison': {
                                'success': file_info['status'] == 'ready',
                                'has_differences': True,  # Will be determined when file is loaded
                                'difference_count': 0,
                                'error': None if file_info['status'] == 'ready' else 'Processing error'
                            },
                            'performance': {
                                'response_count': file_info.get('response_count', 0)
                            },
                            'all_success': file_info['status'] == 'ready'
                        })
                
                # Get basic stats
                stats = self.file_processor.get_basic_stats()
                
                # Convert stats to expected format
                stats_formatted = {
                    'total_docs': stats['total_files'],
                    'success_rate': stats['success_rate'],
                    'failed_count': stats['error_files'],
                    'domain_stats': {}  # Add domain stats if needed
                }
                
                # IMPORTANT: Get all saved progress for initial loading
                all_progress = self.storage_manager.get_all_progress()
                print(f"Loading initial progress: {len(all_progress)} files with saved data")
                
                return render_template('viewer_template.html', 
                                     folder_groups=folder_groups,
                                     stats=stats_formatted,
                                     initial_progress=all_progress)  # Pass to template
                                     
            except Exception as e:
                print(f"Error in index route: {e}")
                return f"<h1>Error</h1><p>Failed to load page: {str(e)}</p><p>Template dir: {self.template_dir}</p>"
        
        @self.app.route('/api/file/<path:file_path>')
        def get_file_diff(file_path):
            """Get diff data for a specific file"""
            try:
                print("file_path--", file_path)
                # Process file on-demand
                diff_data = self.file_processor.process_file(file_path)
                
                if diff_data and diff_data.get('success'):
                    # Get saved progress for this file
                    progress = self.storage_manager.get_file_progress(file_path)
                    diff_data['progress'] = progress
                    
                    return jsonify({
                        'success': True,
                        'data': diff_data
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': diff_data.get('error', 'File not found or could not be processed')
                    }), 404
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/progress/save', methods=['POST'])
        def save_progress():
            """Save progress for a file"""
            try:
                data = request.json
                file_key = data.get('file_key')
                flag = data.get('flag')
                comment = data.get('comment')
                resolved = data.get('resolved')
                resolved_diffs = data.get('resolved_diffs')
                
                print(f"Saving progress for file_key: '{file_key}'")  # Debug log
                print(f"Data: flag={flag}, comment={comment}, resolved={resolved}")
                
                if not file_key:
                    return jsonify({'success': False, 'error': 'file_key is required'}), 400
                
                success = self.storage_manager.save_file_progress(
                    file_key, flag, comment, resolved, resolved_diffs
                )
                
                if success:
                    print(f"Successfully saved progress for: {file_key}")
                
                return jsonify({
                    'success': success,
                    'message': 'Progress saved successfully'
                })
                
            except Exception as e:
                print(f"Error saving progress: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/progress/load/<path:file_key>')
        def load_progress(file_key):
            """Load progress for a file"""
            try:
                progress = self.storage_manager.get_file_progress(file_key)
                return jsonify({
                    'success': True,
                    'data': progress
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/progress/all')
        def get_all_progress():
            """Get all progress data"""
            try:
                all_progress = self.storage_manager.get_all_progress()
                return jsonify({
                    'success': True,
                    'data': all_progress
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/session/save', methods=['POST'])
        def save_session():
            """Save a complete session"""
            try:
                data = request.json
                session_name = data.get('session_name')
                
                if not session_name:
                    return jsonify({'success': False, 'error': 'session_name is required'}), 400
                
                # Get all current progress
                all_progress = self.storage_manager.get_all_progress()
                stats = self.file_processor.get_basic_stats()
                
                success = self.storage_manager.save_session(session_name, all_progress, stats)
                
                return jsonify({
                    'success': success,
                    'message': f'Session "{session_name}" saved successfully'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/session/load/<session_name>')
        def load_session(session_name):
            """Load a session"""
            try:
                session_data = self.storage_manager.load_session(session_name)
                
                if session_data:
                    # Apply loaded progress to database
                    for file_key, progress in session_data['progress_data'].items():
                        self.storage_manager.save_file_progress(
                            file_key,
                            progress.get('flag'),
                            progress.get('comment'),
                            progress.get('resolved'),
                            progress.get('resolved_diffs')
                        )
                    
                    return jsonify({
                        'success': True,
                        'data': session_data,
                        'message': f'Session "{session_name}" loaded successfully'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Session not found'
                    }), 404
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/session/list')
        def list_sessions():
            """List all sessions"""
            try:
                sessions = self.storage_manager.list_sessions()
                return jsonify({
                    'success': True,
                    'data': sessions
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/session/delete/<session_name>', methods=['DELETE'])
        def delete_session(session_name):
            """Delete a session"""
            try:
                success = self.storage_manager.delete_session(session_name)
                return jsonify({
                    'success': success,
                    'message': f'Session "{session_name}" deleted successfully'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/export')
        def export_data():
            """Export all data to JSON"""
            try:
                import tempfile
                from datetime import datetime
                
                # Create temporary file
                filename = f"api_diff_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                
                success = self.storage_manager.export_to_json(temp_path)
                
                if success:
                    return send_from_directory(
                        tempfile.gettempdir(), 
                        filename, 
                        as_attachment=True,
                        download_name=filename
                    )
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Export failed'
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def run(self, host='127.0.0.1', port=5000, debug=True):
        """Run the Flask application"""
        print(f"Starting API Diff Viewer...")
        print(f"Results directory: {self.results_dir}")
        print(f"Template directory: {self.template_dir}")
        print(f"Static directory: {self.static_dir}")
        print(f"Server: http://{host}:{port}")
        print(f"Database: {self.storage_manager.db_path}")
        
        self.app.run(host=host, port=port, debug=debug)