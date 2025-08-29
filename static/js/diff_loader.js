// This file handles the loading of differences from storage when a file is clicked. 
// It makes AJAX requests to the server to fetch the necessary data without reloading the entire page.

document.addEventListener('DOMContentLoaded', function() {
    // Function to load differences for a specific file
    function loadDifferences(folder, filename) {
        const url = `/api/diff/${folder}/${filename}`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                displayDifferences(data);
            })
            .catch(error => {
                console.error('Error loading differences:', error);
                showError('Failed to load differences. Please try again.');
            });
    }

    // Function to display the differences in the viewer
    function displayDifferences(data) {
        const diffContent = document.getElementById('diffContent');
        diffContent.innerHTML = ''; // Clear previous content

        if (data && data.differences) {
            data.differences.forEach(diff => {
                const diffItem = document.createElement('div');
                diffItem.className = 'diff-item';
                diffItem.innerHTML = `
                    <div class="diff-path">${diff.path}</div>
                    <div class="diff-values">
                        <div class="diff-value diff-left">${escapeHtml(diff.left)}</div>
                        <div class="diff-value diff-right">${escapeHtml(diff.right)}</div>
                    </div>
                `;
                diffContent.appendChild(diffItem);
            });
        } else {
            diffContent.innerHTML = '<div class="no-diff">No differences found.</div>';
        }
    }

    // Function to escape HTML for safe rendering
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    // Event listener for file items
    document.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('click', function() {
            const folder = this.getAttribute('data-folder');
            const filename = this.getAttribute('data-filename');
            if (folder && filename) {
                loadDifferences(folder, filename);
            }
        });
    });
});