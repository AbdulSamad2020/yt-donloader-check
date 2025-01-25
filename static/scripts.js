function fetchFormats() {
    console.log("Fetch Formats button clicked");
    const url = document.getElementById('url').value.trim();
    const statusMessage = document.getElementById('statusMessage');

    if (!url) {
        alert('Please enter a valid YouTube URL.');
        return;
    }

    statusMessage.textContent = 'Fetching formats...';

    fetch('/formats', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Failed to fetch formats.'); });
            }
            return response.json();
        })
        .then(data => {
            console.log("Formats fetched:", data);
            statusMessage.textContent = 'Formats fetched. Please select one.';
            const formatsDiv = document.getElementById('formats');
            formatsDiv.innerHTML = '';
            if (Array.isArray(data)) {
                data.forEach(format => {
                    const button = document.createElement('button');
                    button.textContent = `${format.resolution} (${format.fps} FPS) - ${format.type}`;
                    button.className = 'btn';
                    button.onclick = () => {
                        selectFormat(format.id);
                        document.getElementById('downloadButton').style.display = 'block';
                        statusMessage.textContent = 'Format selected. Ready to download.';
                    };
                    formatsDiv.appendChild(button);
                });
            } else {
                formatsDiv.textContent = 'Error fetching formats: ' + data;
            }
        })
        .catch(error => {
            console.error('Error fetching formats:', error);
            alert('Error fetching formats: ' + error.message);
            statusMessage.textContent = 'Error fetching formats.';
        });
}

function selectFormat(formatId) {
    console.log("Format selected:", formatId);
    sessionStorage.setItem('selectedFormat', formatId);
    alert(`Format ${formatId} selected`);
}

function toggleTrimInputs() {
    const trimInputs = document.getElementById('trimInputs');
    trimInputs.style.display = trimInputs.style.display === 'none' ? 'block' : 'none';
}

function downloadVideo() {
    console.log("Download Video button clicked");
    const url = document.getElementById('url').value.trim();
    const outputFilename = document.getElementById('output_filename').value.trim();
    const formatId = sessionStorage.getItem('selectedFormat');
    const statusMessage = document.getElementById('statusMessage');
    const trimCheckbox = document.getElementById('trimCheckbox').checked;
    const trimStart = document.getElementById('trimStart').value.trim();
    const trimEnd = document.getElementById('trimEnd').value.trim();

    if (!url) {
        alert('Please enter a valid YouTube URL.');
        return;
    }

    if (!outputFilename) {
        alert('Please enter a valid output filename.');
        return;
    }

    if (!formatId) {
        alert('Please select a format first.');
        return;
    }

    if (trimCheckbox && (!trimStart || !trimEnd)) {
        alert('Please enter both start and end times for trimming.');
        return;
    }

    statusMessage.textContent = 'Downloading video...';

    fetch('/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: url,
            format_id: formatId,
            output_filename: outputFilename,
            trim_start: trimCheckbox ? trimStart : null,
            trim_end: trimCheckbox ? trimEnd : null
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Failed to download video.'); });
            }
            return response.blob();
        })
        .then(blob => {
            console.log("Video downloaded");
            statusMessage.textContent = 'Download complete. Click the button to save the video.';
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${outputFilename}.mp4`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(error => {
            console.error('Error downloading video:', error);
            alert('Error downloading video: ' + error.message);
            statusMessage.textContent = 'Error downloading video.';
        });
}