// This file contains the main JavaScript logic for the application. It handles user interactions, such as clicking on file items and displaying differences. 

class DiffViewer {
    constructor() {
        this.currentFile = null;
        this.currentDifferences = [];
        this.progressData = {};
        this.init();
    }
    
    async init() {
        console.log('Initializing DiffViewer...');
        this.setupEventListeners();
        await this.loadAllProgress();
        this.updateUI();
    }
    
    setupEventListeners() {
        // Folder toggle
        document.querySelectorAll('.folder-header').forEach(header => {
            header.addEventListener('click', (e) => {
                e.preventDefault();
                const folderId = header.getAttribute('data-folder');
                this.toggleFolder(folderId);
            });
        });
        
        // File selection - use event delegation for dynamically loaded content
        document.addEventListener('click', (e) => {
            if (e.target.closest('.file-item')) {
                const fileItem = e.target.closest('.file-item');
                const filePath = fileItem.getAttribute('data-file-path');
                if (filePath) {
                    e.preventDefault();
                    this.selectFile(filePath);
                }
            }
        });
        
        // Progress controls
        const flagSelect = document.getElementById('flagSelect');
        if (flagSelect) {
            flagSelect.addEventListener('change', (e) => {
                console.log('Flag changed:', e.target.value);
                this.updateFlag();
            });
        }
        
        const commentInput = document.getElementById('commentInput');
        if (commentInput) {
            commentInput.addEventListener('input', () => this.debounceUpdateComment());
        }
        
        const resolveBtn = document.getElementById('resolveBtn');
        if (resolveBtn) {
            resolveBtn.addEventListener('click', () => this.toggleResolved());
        }
        
        // Session controls
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSession());
        }
        
        // Add other controls if they exist in your template
        this.setupAdditionalControls();
    }
    
    setupAdditionalControls() {
        // Setup any additional controls that might be in your template
        const exportBtn = document.querySelector('[data-action="export"]');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportData());
        }
        
        const loadBtn = document.querySelector('[data-action="load"]');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadSessionDialog());
        }
    }
    
    // Debounce comment updates
    debounceUpdateComment() {
        clearTimeout(this.commentTimeout);
        this.commentTimeout = setTimeout(() => this.updateComment(), 500);
    }
    
    async loadAllProgress() {
        try {
            console.log('Loading all progress...');
            const response = await fetch('/api/progress/all');
            const result = await response.json();
            
            if (result.success) {
                this.progressData = result.data;
                console.log('Progress loaded:', Object.keys(this.progressData).length, 'files');
                this.updateFileStates();
            } else {
                console.error('Failed to load progress:', result.error);
            }
        } catch (error) {
            console.error('Failed to load progress:', error);
        }
    }
    
    updateFileStates() {
        console.log('Updating file states...');
        // Update file item visual states based on progress
        document.querySelectorAll('.file-item').forEach(item => {
            const filePath = item.getAttribute('data-file-path');
            const progress = this.progressData[filePath];
            
            if (progress) {
                // Remove existing flag classes
                item.classList.remove('flag-high', 'flag-medium', 'flag-low');
                
                // Add flag class if set
                if (progress.flag) {
                    item.classList.add(`flag-${progress.flag}`);
                    console.log(`Applied flag-${progress.flag} to ${filePath}`);
                }
                
                // Add resolved class if resolved
                if (progress.resolved) {
                    item.classList.add('resolved');
                } else {
                    item.classList.remove('resolved');
                }
            }
        });
        
        this.updateFolderColors();
    }
    
    updateFolderColors() {
        // Update folder header colors based on contained file flags
        const folderFlags = {};
        
        // Collect flags for each folder
        for (const [filePath, progress] of Object.entries(this.progressData)) {
            if (progress.flag) {
                const folder = filePath.split('_')[0]; // First part before underscore
                if (!folderFlags[folder]) folderFlags[folder] = [];
                folderFlags[folder].push(progress.flag);
            }
        }
        
        // Apply folder colors
        document.querySelectorAll('.folder-header').forEach(header => {
            const folder = header.getAttribute('data-folder');
            header.classList.remove('has-high', 'has-medium', 'has-low');
            
            if (folderFlags[folder]) {
                if (folderFlags[folder].includes('high')) {
                    header.classList.add('has-high');
                } else if (folderFlags[folder].includes('medium')) {
                    header.classList.add('has-medium');
                } else if (folderFlags[folder].includes('low')) {
                    header.classList.add('has-low');
                }
            }
        });
    }
    
    toggleFolder(folderId) {
        const content = document.getElementById(`content-${folderId}`);
        const header = document.querySelector(`[data-folder="${folderId}"]`);
        
        if (content && header) {
            const isActive = content.classList.contains('active');
            content.classList.toggle('active');
            header.classList.toggle('active');
            
            console.log(`Folder ${folderId} ${isActive ? 'collapsed' : 'expanded'}`);
        }
    }
    
    async selectFile(filePath) {
        try {
            console.log('Selecting file:', filePath);
            
            // Update active file selection
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('active');
            });
            
            const fileElement = document.querySelector(`[data-file-path="${filePath}"]`);
            if (fileElement) {
                fileElement.classList.add('active');
            }
            
            this.currentFile = filePath;
            
            // Show loading state
            const diffContent = document.getElementById('diffContent');
            if (diffContent) {
                diffContent.innerHTML = '<div class="loading">Loading file...</div>';
            }
            
            // Load file data
            const response = await fetch(`/api/file/${encodeURIComponent(filePath)}`);
            const result = await response.json();
            
            if (result.success) {
                this.displayDiff(result.data);
                this.updateControls(result.data.progress);
            } else {
                if (diffContent) {
                    diffContent.innerHTML = `<div class="error">Error: ${result.error}</div>`;
                }
            }
            
        } catch (error) {
            console.error('Failed to load file:', error);
            const diffContent = document.getElementById('diffContent');
            if (diffContent) {
                diffContent.innerHTML = '<div class="error">Failed to load file</div>';
            }
        }
    }
    
    displayDiff(data) {
        const diffContent = document.getElementById('diffContent');
        if (!diffContent) return;
        
        if (!data.success) {
            // Show error state
            diffContent.innerHTML = `
                <div class="error-state">
                    <h3>Processing Errors</h3>
                    <p>One or more APIs failed to process this file.</p>
                    <pre>${data.error || 'Unknown error'}</pre>
                </div>
            `;
            return;
        }
        
        if (!data.has_differences) {
            // Show identical state
            diffContent.innerHTML = `
                <div class="no-diff">
                    <h3>Files are Identical</h3>
                    <p>Both API responses returned the same result.</p>
                </div>
            `;
            return;
        }
        
        // Show side-by-side diff
        this.currentDifferences = data.differences || [];
        this.renderSideBySideDiff(data);
    }
    
    renderSideBySideDiff(data) {
        const leftContent = this.renderDiffSide(data.left_content, data.left_api, 'left');
        const rightContent = this.renderDiffSide(data.right_content, data.right_api, 'right');

        const diffContent = document.getElementById('diffContent');
        if (diffContent) {
            diffContent.innerHTML = `
                <div class="diff-container">
                    <div class="diff-side" id="leftDiffSide">
                        <h3>${data.left_api}</h3>
                        <div class="diff-content">${leftContent}</div>
                    </div>
                    <div class="diff-gutter"></div>
                    <div class="diff-side" id="rightDiffSide">
                        <h3>${data.right_api}</h3>
                        <div class="diff-content">${rightContent}</div>
                    </div>
                </div>
            `;
        }
        
        this.synchronizeScroll();
        this.updateDifferencesList();
    }
    
    renderDiffSide(lines, apiName, side) {
        if (!Array.isArray(lines)) {
            return '<div class="error">Invalid content format</div>';
        }
        
        return lines.map((line, index) => {
            const hasHighlight = this.currentDifferences.some(d => 
                (side === 'left' && d.line_left === index) || 
                (side === 'right' && d.line_right === index)
            );
            
            const highlightClass = hasHighlight ? 'highlight' : '';
            
            return `<div class="line ${highlightClass}" data-line="${index}" data-side="${side}">
                <span class="line-number">${index + 1}</span>
                <span class="line-content">${this.escapeHtml(line)}</span>
            </div>`;
        }).join('');
    }
    
    updateControls(progress) {
        // Show diff controls
        const diffControls = document.getElementById('diffControls');
        if (diffControls) {
            diffControls.style.display = 'flex';
        }
        
        // Update flag selector
        const flagSelect = document.getElementById('flagSelect');
        if (flagSelect) {
            flagSelect.value = progress.flag || '';
        }
        
        // Update comment input
        const commentInput = document.getElementById('commentInput');
        if (commentInput) {
            commentInput.value = progress.comment || '';
        }
        
        // Update resolve button
        const resolveBtn = document.getElementById('resolveBtn');
        if (resolveBtn) {
            if (progress.resolved) {
                resolveBtn.textContent = 'Unresolve All';
                resolveBtn.classList.add('resolved');
            } else {
                resolveBtn.textContent = 'Resolve All';
                resolveBtn.classList.remove('resolved');
            }
        }
    }
    
    async updateFlag() {
        if (!this.currentFile) return;
        
        const flagSelect = document.getElementById('flagSelect');
        const flag = flagSelect ? flagSelect.value : '';
        
        console.log('Updating flag for', this.currentFile, 'to', flag);
        
        try {
            const response = await fetch('/api/progress/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_key: this.currentFile,
                    flag: flag || null
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update local progress data
                if (!this.progressData[this.currentFile]) {
                    this.progressData[this.currentFile] = {};
                }
                this.progressData[this.currentFile].flag = flag || null;
                
                // Immediately update visual state
                this.updateFileStates();
                this.showSaveIndicator('Flag updated');
                console.log('Flag saved successfully');
            } else {
                console.error('Failed to save flag:', result.error);
            }
        } catch (error) {
            console.error('Failed to save flag:', error);
        }
    }
    
    async updateComment() {
        if (!this.currentFile) return;
        
        const commentInput = document.getElementById('commentInput');
        const comment = commentInput ? commentInput.value : '';
        
        try {
            const response = await fetch('/api/progress/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_key: this.currentFile,
                    comment: comment
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update local progress data
                if (!this.progressData[this.currentFile]) {
                    this.progressData[this.currentFile] = {};
                }
                this.progressData[this.currentFile].comment = comment;
                
                this.showSaveIndicator('Comment saved');
            }
        } catch (error) {
            console.error('Failed to save comment:', error);
        }
    }
    
    async toggleResolved() {
        if (!this.currentFile) return;
        
        const currentState = this.progressData[this.currentFile]?.resolved || false;
        const newState = !currentState;
        
        try {
            const response = await fetch('/api/progress/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_key: this.currentFile,
                    resolved: newState
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update local progress data
                if (!this.progressData[this.currentFile]) {
                    this.progressData[this.currentFile] = {};
                }
                this.progressData[this.currentFile].resolved = newState;
                
                // Update visual state
                this.updateFileStates();
                
                // Update button
                const resolveBtn = document.getElementById('resolveBtn');
                if (resolveBtn) {
                    if (newState) {
                        resolveBtn.textContent = 'Unresolve All';
                        resolveBtn.classList.add('resolved');
                    } else {
                        resolveBtn.textContent = 'Resolve All';
                        resolveBtn.classList.remove('resolved');
                    }
                }
                
                this.showSaveIndicator(newState ? 'Resolved' : 'Unresolved');
            }
        } catch (error) {
            console.error('Failed to save resolved state:', error);
        }
    }
    
    // Additional methods for differences, sessions, etc.
    updateDifferencesList() {
        // Implementation for differences list if needed
        console.log('Updating differences list:', this.currentDifferences.length, 'differences');
    }
    
    synchronizeScroll() {
        const leftSide = document.getElementById('leftDiffSide');
        const rightSide = document.getElementById('rightDiffSide');
        
        if (!leftSide || !rightSide) return;
        
        let isScrolling = false;
        
        leftSide.addEventListener('scroll', () => {
            if (!isScrolling) {
                isScrolling = true;
                rightSide.scrollTop = leftSide.scrollTop;
                setTimeout(() => isScrolling = false, 10);
            }
        });
        
        rightSide.addEventListener('scroll', () => {
            if (!isScrolling) {
                isScrolling = true;
                leftSide.scrollTop = rightSide.scrollTop;
                setTimeout(() => isScrolling = false, 10);
            }
        });
    }
    
    async saveSession() {
        const sessionName = prompt('Enter session name:');
        if (!sessionName) return;
        
        try {
            const response = await fetch('/api/session/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_name: sessionName })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSaveIndicator('Session saved');
            } else {
                alert(`Failed to save session: ${result.error}`);
            }
        } catch (error) {
            console.error('Failed to save session:', error);
            alert('Failed to save session');
        }
    }
    
    async loadSessionDialog() {
        try {
            const response = await fetch('/api/session/list');
            const result = await response.json();
            
            if (result.success && result.data.length > 0) {
                const sessions = result.data.map(s => `${s[0]} (${s[1]})`).join('\n');
                const sessionName = prompt(`Available sessions:\n${sessions}\n\nEnter session name to load:`);
                
                if (sessionName) {
                    await this.loadSession(sessionName);
                }
            } else {
                alert('No saved sessions found');
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
            alert('Failed to load sessions');
        }
    }
    
    async loadSession(sessionName) {
        try {
            const response = await fetch(`/api/session/load/${encodeURIComponent(sessionName)}`);
            const result = await response.json();
            
            if (result.success) {
                // Reload all progress
                await this.loadAllProgress();
                this.showSaveIndicator('Session loaded');
            } else {
                alert(`Failed to load session: ${result.error}`);
            }
        } catch (error) {
            console.error('Failed to load session:', error);
            alert('Failed to load session');
        }
    }
    
    async exportData() {
        try {
            const response = await fetch('/api/export');
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'export.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showSaveIndicator('Data exported');
            }
        } catch (error) {
            console.error('Failed to export data:', error);
            alert('Failed to export data');
        }
    }
    
    showSaveIndicator(message) {
        const indicator = document.getElementById('saveIndicator');
        if (indicator) {
            indicator.textContent = message;
            indicator.style.display = 'block';
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 1500);
        } else {
            // Fallback - create a temporary indicator
            console.log('Save indicator:', message);
        }
    }
    
    updateUI() {
        // Initial UI update
        this.updateFileStates();
        console.log('UI updated');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Initialize the viewer when DOM is loaded
let diffViewer;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing DiffViewer...');
    diffViewer = new DiffViewer();
});

// Global functions for onclick handlers
window.diffViewer = diffViewer;