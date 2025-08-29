import os
import json
import re
from pathlib import Path
from collections import defaultdict
from file_processor import FileProcessor
import sqlite3
from datetime import datetime

class StorageManager:
    def __init__(self, results_dir=None):
        # Set database path relative to the main project directory
        if results_dir:
            # Use results_dir parent for database location (same level as api_results)
            base_dir = os.path.dirname(results_dir)
            self.db_path = os.path.join(base_dir, 'progress.db')
        else:
            # Fallback to current directory
            self.db_path = 'progress.db'
        
        print(f"Database path: {self.db_path}")
        self.results_dir = Path(results_dir) if results_dir else None
        self.file_processor = None
        self.folder_groups = defaultdict(list)
        self.init_database()
        self._scan_results()
    
    def init_database(self):
        """Initialize SQLite database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Drop old table if it exists with wrong schema
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_progress'")
                if cursor.fetchone():
                    # Check if the schema is correct
                    cursor.execute("PRAGMA table_info(file_progress)")
                    columns = cursor.fetchall()
                    print(f"Existing table columns: {columns}")
                    
                    # Check if file_key is the primary key (should be column 0 with pk=1)
                    file_key_col = next((col for col in columns if col[1] == 'file_key'), None)
                    if not file_key_col or file_key_col[5] != 1:  # pk field should be 1
                        print("Table schema is incorrect, recreating...")
                        cursor.execute('DROP TABLE file_progress')
                
                # Create file_progress table with TEXT primary key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_progress (
                        file_key TEXT PRIMARY KEY,
                        flag TEXT,
                        comment TEXT,
                        resolved INTEGER DEFAULT 0,
                        resolved_diffs TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_name TEXT PRIMARY KEY,
                        progress_data TEXT,
                        stats_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                print("Database initialized successfully")
                
                # Verify the schema
                cursor.execute("PRAGMA table_info(file_progress)")
                columns = cursor.fetchall()
                print(f"Final table schema: {columns}")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    
    def _scan_results(self):
        """Scan the results directory and organize folders into groups"""
        if not self.results_dir or not self.results_dir.exists():
            print(f"Results directory not found: {self.results_dir}")
            return
        
        for folder_path in self.results_dir.iterdir():
            if folder_path.is_dir():
                self._process_folder_metadata(folder_path)
    
    def _process_folder_metadata(self, folder_path):
        """Process folder to extract metadata without full comparison"""
        folder_name = folder_path.name
        response_files = [f for f in folder_path.glob('*_response.json')]
        
        if len(response_files) < 2:
            return
        
        # Extract folder grouping info
        parts = folder_name.split('_')
        main_folder = parts[0] if parts else 'unknown'
        sub_filename = '_'.join(parts[1:]) if len(parts) > 1 else folder_name
        
        # Quick success check without full processing
        all_success = True
        has_differences = False
        
        try:
            # Load just the response status
            responses = {}
            for file_path in response_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_name = self._extract_api_name(file_path.name)
                    responses[api_name] = data
            
            # Quick comparison check
            if len(responses) >= 2:
                api_names = list(responses.keys())
                obj1 = responses[api_names[0]]
                obj2 = responses[api_names[1]]
                has_differences = not self._quick_equal_check(obj1, obj2)
            
        except Exception as e:
            print(f"Error processing {folder_name}: {e}")
            all_success = False
        
        # Determine status
        if not all_success:
            status_class = "status-failed"
            status_text = "FAIL"
        elif has_differences:
            status_class = "status-diff"
            status_text = "DIFF"
        else:
            status_class = "status-identical"
            status_text = "OK"
        
        # Add to folder groups
        self.folder_groups[main_folder].append({
            'folder_name': folder_name,
            'sub_filename': sub_filename,
            'all_success': all_success,
            'has_differences': has_differences,
            'status_class': status_class,
            'status_text': status_text
        })
    
    def _extract_api_name(self, filename):
        """Extract API name from filename"""
        match = re.match(r'(.+?)_(.+?)_response\.json', filename)
        if match:
            return match.group(2)
        return filename.replace('_response.json', '')
    
    def _quick_equal_check(self, obj1, obj2):
        """Quick equality check without detailed comparison"""
        try:
            # Simple JSON string comparison for quick check
            json1 = json.dumps(obj1, sort_keys=True)
            json2 = json.dumps(obj2, sort_keys=True)
            return json1 == json2
        except:
            return False
    
    def load_folder_groups(self):
        """Return the folder groups for the UI"""
        return dict(self.folder_groups)
    
    def load_differences(self, folder, filename):
        """Load and process differences for a specific file on-demand"""
        folder_path = self.results_dir / folder
        
        if not folder_path.exists():
            print(f"Folder not found: {folder_path}")
            return None
        
        response_files = list(folder_path.glob('*_response.json'))
        
        if len(response_files) < 2:
            return {
                'error': 'Insufficient response files',
                'has_differences': False
            }
        
        try:
            # Load responses
            responses = {}
            performance = {}
            
            for file_path in response_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_name = self._extract_api_name(file_path.name)
                    responses[api_name] = data
                    
                    # Mock performance data (you can enhance this)
                    performance[api_name] = {
                        'success': True,
                        'status_code': 200,
                        'duration': 1.0
                    }
            
            # Process comparison
            all_success = len(responses) >= 2 and all(
                perf.get('success', False) for perf in performance.values()
            )
            
            if not all_success:
                return {
                    'all_success': False,
                    'performance': performance,
                    'has_differences': False
                }
            
            # Get the first two APIs for comparison
            api_names = list(responses.keys())
            if len(api_names) >= 2:
                comparison = self.file_processor.create_highlighted_json(
                    responses[api_names[0]], 
                    responses[api_names[1]],
                    api_names[0],
                    api_names[1]
                )
                
                return {
                    'all_success': True,
                    'performance': performance,
                    'comparison': comparison,
                    'has_differences': comparison['has_differences']
                }
            
            return {
                'all_success': True,
                'performance': performance,
                'has_differences': False
            }
            
        except Exception as e:
            print(f"Error loading differences for {folder}/{filename}: {e}")
            return {
                'error': str(e),
                'all_success': False,
                'has_differences': False
            }
    
    def get_stats(self):
        """Calculate and return statistics"""
        total_docs = sum(len(items) for items in self.folder_groups.values())
        success_count = 0
        failed_count = 0
        
        for items in self.folder_groups.values():
            for item in items:
                if item['all_success']:
                    success_count += 1
                else:
                    failed_count += 1
        
        success_rate = round((success_count / total_docs * 100) if total_docs > 0 else 0, 1)
        
        return {
            'total_docs': total_docs,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_rate,
            'domain_stats': {}  # Can be enhanced later
        }
    
    def save_file_progress(self, file_key, flag=None, comment=None, resolved=None, resolved_diffs=None):
        """Save progress for a specific file"""
        try:
            print(f"StorageManager: Saving progress for file_key: '{file_key}'")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if record exists using file_key as the primary key
                cursor.execute('SELECT file_key, flag, comment, resolved, resolved_diffs FROM file_progress WHERE file_key = ?', (file_key,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record - only update provided fields
                    updates = []
                    params = []
                    
                    if flag is not None:
                        updates.append('flag = ?')
                        params.append(flag)
                        print(f"  Updating flag to: {flag}")
                    
                    if comment is not None:
                        updates.append('comment = ?')
                        params.append(comment)
                        print(f"  Updating comment to: {comment}")
                    
                    if resolved is not None:
                        updates.append('resolved = ?')
                        params.append(1 if resolved else 0)
                        print(f"  Updating resolved to: {resolved}")
                    
                    if resolved_diffs is not None:
                        updates.append('resolved_diffs = ?')
                        params.append(json.dumps(resolved_diffs))
                        print(f"  Updating resolved_diffs")
                    
                    if updates:
                        updates.append('last_updated = CURRENT_TIMESTAMP')
                        params.append(file_key)
                        
                        query = f'UPDATE file_progress SET {", ".join(updates)} WHERE file_key = ?'
                        print(f"  SQL: {query}")
                        print(f"  Params: {params}")
                        cursor.execute(query, params)
                else:
                    # Insert new record using file_key as primary key
                    print(f"  Inserting new record for: {file_key}")
                    cursor.execute('''
                        INSERT INTO file_progress (file_key, flag, comment, resolved, resolved_diffs)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        file_key,
                        flag,
                        comment,
                        1 if resolved else 0,
                        json.dumps(resolved_diffs) if resolved_diffs else None
                    ))
                
                conn.commit()
                
                # Verify the save worked
                cursor.execute('SELECT * FROM file_progress WHERE file_key = ?', (file_key,))
                saved_row = cursor.fetchone()
                print(f"Verified saved data: {saved_row}")
                
                return True
                
        except Exception as e:
            print(f"Error saving file progress for {file_key}: {e}")
            return False
    
    def get_file_progress(self, file_key):
        """Get progress for a specific file"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM file_progress WHERE file_key = ?', (file_key,))
                row = cursor.fetchone()
                
                if row:
                    resolved_diffs = {}
                    if row[4]:  # resolved_diffs column
                        try:
                            resolved_diffs = json.loads(row[4])
                        except:
                            resolved_diffs = {}
                    
                    return {
                        'flag': row[1],
                        'comment': row[2],
                        'resolved': bool(row[3]),
                        'resolved_diffs': resolved_diffs,
                        'last_updated': row[5]
                    }
                else:
                    return {
                        'flag': None,
                        'comment': '',
                        'resolved': False,
                        'resolved_diffs': {},
                        'last_updated': None
                    }
                    
        except Exception as e:
            print(f"Error getting file progress: {e}")
            return {
                'flag': None,
                'comment': '',
                'resolved': False,
                'resolved_diffs': {},
                'last_updated': None
            }
    
    def get_all_progress(self):
        """Get all progress data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM file_progress')
                rows = cursor.fetchall()
                
                all_progress = {}
                for row in rows:
                    resolved_diffs = {}
                    if row[4]:  # resolved_diffs column
                        try:
                            resolved_diffs = json.loads(row[4])
                        except:
                            resolved_diffs = {}
                    
                    all_progress[row[0]] = {  # file_key is row[0] now
                        'flag': row[1],
                        'comment': row[2],
                        'resolved': bool(row[3]),
                        'resolved_diffs': resolved_diffs,
                        'last_updated': row[5]
                    }
                
                print(f"Retrieved progress for {len(all_progress)} files")
                print(f"File keys: {list(all_progress.keys())}")
                return all_progress
                
        except Exception as e:
            print(f"Error getting all progress: {e}")
            return {}
    
    def save_session(self, session_name, progress_data, stats=None):
        """Save a complete session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        progress_json = json.dumps(progress_data)
        stats_json = json.dumps(stats) if stats else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_name, progress_data, stats, created_at)
            VALUES (?, ?, ?, ?)
        ''', (session_name, progress_json, stats_json, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return True
    
    def load_session(self, session_name):
        """Load a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT progress_data, stats FROM sessions 
            WHERE session_name = ?
        ''', (session_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            progress_json, stats_json = result
            try:
                progress_data = json.loads(progress_json)
                stats = json.loads(stats_json) if stats_json else None
                return {'progress_data': progress_data, 'stats': stats}
            except:
                return None
        
        return None
    
    def list_sessions(self):
        """List all sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT session_name, created_at FROM sessions ORDER BY created_at DESC')
        results = cursor.fetchall()
        conn.close()
        
        return [(name, created_at) for name, created_at in results]
    
    def delete_session(self, session_name):
        """Delete a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sessions WHERE session_name = ?', (session_name,))
        conn.commit()
        conn.close()
        
        return True
    
    def export_to_json(self, output_file):
        """Export all data to JSON"""
        export_data = {
            'progress': self.get_all_progress(),
            'sessions': {},
            'exported_at': datetime.now().isoformat()
        }
        
        # Get sessions
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT session_name, progress_data, stats, created_at FROM sessions')
        
        for session_name, progress_json, stats_json, created_at in cursor.fetchall():
            try:
                progress_data = json.loads(progress_json)
                stats = json.loads(stats_json) if stats_json else None
                export_data['sessions'][session_name] = {
                    'progress_data': progress_data,
                    'stats': stats,
                    'created_at': created_at
                }
            except:
                continue
        
        conn.close()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return True
    
    def import_from_json(self, input_file):
        """Import data from JSON"""
        with open(input_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # Import progress
        for file_key, progress in import_data.get('progress', {}).items():
            self.save_file_progress(
                file_key,
                progress.get('flag'),
                progress.get('comment'),
                progress.get('resolved'),
                progress.get('resolved_diffs')
            )
        
        # Import sessions
        for session_name, session_data in import_data.get('sessions', {}).items():
            self.save_session(
                session_name,
                session_data.get('progress_data', {}),
                session_data.get('stats')
            )
        
        return True