import os
import json
import re
import difflib
from pathlib import Path
from collections import defaultdict

class FileProcessor:
    def __init__(self, results_dir):
        self.results_dir = results_dir
        # self.ignore_patterns = [
        #     r'data\[\d+\]\.OCRData\[\d+\]\.location',
        #     r'data\[\d+\]\.OCRData\[\d+\]\.confidence'
        # ]
        # self.ignore_patterns = [
        #     r'\.location(\.|$|\[)',      # Any path ending with .location or .location[...]
        #     r'\.confidence(\.|$|\[)',    # Any path ending with .confidence or .confidence[...]
        #     r'Font Check',               # Any path containing Font Check
        #     r'\.name(\.|$|\[)',          # Any path ending with .name or .name[...]
        # ]
        self.ignore_patterns = []
    
    def get_average_processing_times(self):
        """Calculate average processing times for local and remote APIs, ignoring pairs where either failed"""
        local_times = []
        remote_times = []
        for folder_name in os.listdir(self.results_dir):
            folder_path = os.path.join(self.results_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            # Find local and remote response files for this folder
            response_files = [f for f in os.listdir(folder_path) if f.endswith('_response.json')]
            local_file = next((f for f in response_files if 'local' in f), None)
            remote_file = next((f for f in response_files if 'remote' in f), None)
            if local_file and remote_file:
                try:
                    with open(os.path.join(folder_path, local_file), 'r', encoding='utf-8') as f_local, \
                        open(os.path.join(folder_path, remote_file), 'r', encoding='utf-8') as f_remote:
                        local_data = json.load(f_local)
                        remote_data = json.load(f_remote)
                        # Only count if BOTH succeeded
                        if local_data.get('success', True) and remote_data.get('success', True):
                            local_time = local_data.get('processing_time_seconds')
                            remote_time = remote_data.get('processing_time_seconds')
                            if local_time is not None and remote_time is not None:
                                local_times.append(local_time)
                                remote_times.append(remote_time)
                except Exception:
                    continue
        avg_local = round(sum(local_times) / len(local_times), 2) if local_times else None
        avg_remote = round(sum(remote_times) / len(remote_times), 2) if remote_times else None
        return {'avg_local': avg_local, 'avg_remote': avg_remote}

    def should_ignore_path(self, path):
        """Check if this path should be ignored"""
        for pattern in self.ignore_patterns:
            if re.match(pattern, path):
                return True
        return False
    
    def get_file_structure(self):
        """Get the organized file structure for the sidebar"""
        structure = defaultdict(list)
        
        if not os.path.exists(self.results_dir):
            return structure
        
        try:
            # Get all folders in results directory
            for folder_name in os.listdir(self.results_dir):
                folder_path = os.path.join(self.results_dir, folder_name)
                
                if not os.path.isdir(folder_path):
                    continue
                
                # Check if folder has JSON response files
                response_files = [f for f in os.listdir(folder_path) 
                                if f.endswith('_response.json')]
                
                if len(response_files) >= 1:  # At least one response file
                    # Extract main folder and sub filename
                    parts = folder_name.split('_', 1)
                    main_folder = parts[0] if parts else 'uncategorized'
                    sub_filename = parts[1] if len(parts) > 1 else folder_name
                    
                    # Analyze the folder
                    analysis = self._analyze_folder_quick(folder_path, folder_name)
                    
                    structure[main_folder].append({
                        'folder_name': folder_name,
                        'sub_filename': sub_filename,
                        'file_path': folder_name,  # This will be used as the file key
                        'response_count': len(response_files),
                        'has_comparison': len(response_files) >= 2,
                        'status': analysis.get('status', 'unknown')
                    })
            
            # Sort each group
            for main_folder in structure:
                structure[main_folder].sort(key=lambda x: x['sub_filename'])
                
        except Exception as e:
            print(f"Error building file structure: {e}")
        
        return dict(structure)
    
    def _analyze_folder_quick(self, folder_path, folder_name):
        """Quick analysis of folder for status"""
        try:
            response_files = [f for f in os.listdir(folder_path) 
                            if f.endswith('_response.json')]
            
            if len(response_files) < 2:
                return {'status': 'incomplete'}
            
            # Check if files exist and are valid JSON
            valid_responses = 0
            api_failed = False
            for file in response_files:
                try:
                    with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if not data.get('success', True):
                            api_failed = True
                        else:
                            valid_responses += 1
                except:
                    api_failed = True  # Treat as failed if not valid JSON
                    # pass

            
            if api_failed:
                return {'status': 'error'}
            elif valid_responses >= 2:
                return {'status': 'ready'}
            else:
                return {'status': 'error'}
                
        except Exception:
            return {'status': 'error'}
    
    def get_basic_stats(self):
        """Get basic statistics about the results"""
        structure = self.get_file_structure()
        
        total_files = sum(len(files) for files in structure.values())
        ready_files = 0
        error_files = 0
        
        for folder_files in structure.values():
            for file_info in folder_files:
                if file_info['status'] == 'ready':
                    ready_files += 1
                elif file_info['status'] == 'error':
                    error_files += 1
        
        return {
            'total_folders': len(structure),
            'total_files': total_files,
            'ready_files': ready_files,
            'error_files': error_files,
            'success_rate': round((ready_files / total_files * 100), 2) if total_files > 0 else 0
        }
    
    def find_differences(self, obj1, obj2, path=""):
        """Find specific differences between two objects (from your working code)"""
        differences = []
        
        if type(obj1) != type(obj2):
            if not self.should_ignore_path(path):
                differences.append({
                    'path': path,
                    'type': 'type_change',
                    'left': str(obj1),
                    'right': str(obj2),
                    'line_left': None,
                    'line_right': None
                })
            return differences
        
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            all_keys = set(obj1.keys()) | set(obj2.keys())
            for key in all_keys:
                current_path = f"{path}.{key}" if path else key
                
                if key not in obj1:
                    if not self.should_ignore_path(current_path):
                        differences.append({
                            'path': current_path,
                            'type': 'missing_left',
                            'left': 'MISSING',
                            'right': str(obj2[key])[:100] + "..." if len(str(obj2[key])) > 100 else str(obj2[key]),
                            'line_left': None,
                            'line_right': None
                        })
                elif key not in obj2:
                    if not self.should_ignore_path(current_path):
                        differences.append({
                            'path': current_path,
                            'type': 'missing_right',
                            'left': str(obj1[key])[:100] + "..." if len(str(obj1[key])) > 100 else str(obj1[key]),
                            'right': 'MISSING',
                            'line_left': None,
                            'line_right': None
                        })
                else:
                    differences.extend(self.find_differences(obj1[key], obj2[key], current_path))
        
        elif isinstance(obj1, list) and isinstance(obj2, list):
            max_len = max(len(obj1), len(obj2))
            for i in range(max_len):
                current_path = f"{path}[{i}]"
                
                if i >= len(obj1):
                    if not self.should_ignore_path(current_path):
                        differences.append({
                            'path': current_path,
                            'type': 'missing_left',
                            'left': 'MISSING',
                            'right': str(obj2[i])[:100] + "..." if len(str(obj2[i])) > 100 else str(obj2[i]),
                            'line_left': None,
                            'line_right': None
                        })
                elif i >= len(obj2):
                    if not self.should_ignore_path(current_path):
                        differences.append({
                            'path': current_path,
                            'type': 'missing_right',
                            'left': str(obj1[i])[:100] + "..." if len(str(obj1[i])) > 100 else str(obj1[i]),
                            'right': 'MISSING',
                            'line_left': None,
                            'line_right': None
                        })
                else:
                    differences.extend(self.find_differences(obj1[i], obj2[i], current_path))
        
        else:
            if obj1 != obj2 and not self.should_ignore_path(path):
                differences.append({
                    'path': path,
                    'type': 'value_change',
                    'left': str(obj1),
                    'right': str(obj2),
                    'line_left': None,
                    'line_right': None
                })
        
        return differences
    
    def create_highlighted_json(self, obj1, obj2):
        """Create side-by-side JSON with differences highlighted using line-by-line diff (from your working code)"""
        # Generate clean JSON strings
        json1 = json.dumps(obj1, indent=2, ensure_ascii=False, sort_keys=True)
        json2 = json.dumps(obj2, indent=2, ensure_ascii=False, sort_keys=True)
        
        # Find structural differences
        structural_differences = self.find_differences(obj1, obj2)
        
        # Convert to lines
        lines1 = json1.split('\n')
        lines2 = json2.split('\n')
        
        # Use difflib to get line-by-line differences
        differ = difflib.SequenceMatcher(None, lines1, lines2)
        line_differences = []
        
        # Get opcodes for line differences
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag in ['delete', 'replace']:
                for line_idx in range(i1, i2):
                    line_differences.append({
                        'path': f'line_{line_idx}',
                        'type': 'line_change',
                        'left': lines1[line_idx] if line_idx < len(lines1) else '',
                        'right': '',
                        'line_left': line_idx,
                        'line_right': None
                    })
            
            if tag in ['insert', 'replace']:
                for line_idx in range(j1, j2):
                    # For replace operations, try to pair with the corresponding left line
                    if tag == 'replace' and (line_idx - j1) < (i2 - i1):
                        left_line_idx = i1 + (line_idx - j1)
                        # Update existing difference to include right side
                        for diff in line_differences:
                            if diff['line_left'] == left_line_idx:
                                diff['right'] = lines2[line_idx]
                                diff['line_right'] = line_idx
                                break
                    else:
                        line_differences.append({
                            'path': f'line_{line_idx}',
                            'type': 'line_change',
                            'left': '',
                            'right': lines2[line_idx] if line_idx < len(lines2) else '',
                            'line_left': None,
                            'line_right': line_idx
                        })
        
        # Combine with structural differences for the differences panel
        all_differences = structural_differences + line_differences
        
        return lines1, lines2, all_differences
    
    def process_file(self, file_path):
        """Process a specific file and return diff data"""
        folder_path = os.path.join(self.results_dir, file_path)
        
        if not os.path.exists(folder_path):
            return {
                'success': False,
                'error': f'Folder not found: {folder_path}'
            }
        
        try:
            # Get response files
            response_files = [f for f in os.listdir(folder_path) 
                            if f.endswith('_response.json')]
            
            if len(response_files) < 2:
                return {
                    'success': False,
                    'error': 'Not enough response files for comparison',
                    'file_count': len(response_files)
                }
            
            # Load the first two response files
            responses = {}
            api_names = []
            processing_times = {}

            for i, file in enumerate(response_files[:2]):
                # Extract API name from filename (like your working code)
                api_name = file.replace('_response.json', '').replace(file_path + '_', '')
                api_names.append(api_name)
                
                try:
                    with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                        full_response = json.load(f)
                        # Get the response_data part (like your working code)
                        responses[api_name] = full_response.get('response_data', {})
                        # Extract processing_time_seconds
                        processing_times[api_name] = full_response.get('processing_time_seconds', None)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Failed to load {file}: {str(e)}'
                    }
            
            if len(responses) < 2:
                return {
                    'success': False,
                    'error': 'Could not load enough valid response files'
                }
            
            # Compare the responses using the EXACT same method as your working code
            api1, api2 = api_names[0], api_names[1]
            response1_data = responses[api1]
            response2_data = responses[api2]
            
            # Create highlighted comparison (EXACTLY like your working Python code)
            lines1, lines2, differences = self.create_highlighted_json(response1_data, response2_data)
            
            return {
                'success': True,
                'left_api': api1,
                'right_api': api2,
                'left_content': lines1,  # These are the line arrays
                'right_content': lines2,  # These are the line arrays
                'differences': differences,
                'has_differences': len(differences) > 0,
                'difference_count': len(differences),
                'processing_times': {
                    api1: processing_times.get(api1),
                    api2: processing_times.get(api2)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Processing error: {str(e)}'
            }