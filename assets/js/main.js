// assets/js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    const toggleModeBtn = document.getElementById('toggle-mode');
    const increaseFontBtn = document.getElementById('increase-font');
    const decreaseFontBtn = document.getElementById('decrease-font');

    // Toggle dark/light mode
    toggleModeBtn.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        body.classList.toggle('light-mode');
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
        const currentSize = parseFloat(getComputedStyle(body).fontSize);
        body.style.fontSize = (currentSize + delta) + 'px';
    }
});