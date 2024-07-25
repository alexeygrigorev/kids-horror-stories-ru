// assets/js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    const toggleModeBtn = document.getElementById('toggle-mode');
    const increaseFontBtn = document.getElementById('increase-font');
    const decreaseFontBtn = document.getElementById('decrease-font');

    // Load saved settings without transitions
    loadSettings();

    // Enable transitions after initial load
    setTimeout(() => {
        body.classList.add('transitions-enabled');
    }, 100);

    // Toggle dark/light mode
    toggleModeBtn.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        body.classList.toggle('light-mode');
        saveSettings();
    });

    // Increase font size
    increaseFontBtn.addEventListener('click', () => {
        changeFontSize(1);
    });

    // Decrease font size
    decreaseFontBtn.addEventListener('click', () => {
        changeFontSize(-1);
    });

    function changeFontSize(delta) {
        let fontSize = parseInt(getComputedStyle(body).fontSize);
        fontSize += delta;
        body.style.fontSize = `${fontSize}px`;
        saveSettings();
    }

    function saveSettings() {
        const isDarkMode = body.classList.contains('dark-mode');
        const fontSize = getComputedStyle(body).fontSize;
        localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        localStorage.setItem('fontSize', fontSize);
    }

    function loadSettings() {
        const savedTheme = localStorage.getItem('theme');
        const savedFontSize = localStorage.getItem('fontSize');

        if (savedTheme === 'dark') {
            body.classList.add('dark-mode');
            body.classList.remove('light-mode');
        }

        if (savedFontSize) {
            body.style.fontSize = savedFontSize;
        }
    }
});