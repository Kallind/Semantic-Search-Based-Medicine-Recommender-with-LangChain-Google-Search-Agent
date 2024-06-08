document.getElementById('send-button').addEventListener('click', async () => {
    const userInput = document.getElementById('user-input').value;
    if (userInput.trim() === '') return;

    const chatbox = document.getElementById('chatbox');
    chatbox.innerHTML += `<div class="user-message">${userInput}</div>`;

    document.getElementById('user-input').value = '';

    const loadingIndicator = document.getElementById('loading-indicator');
    loadingIndicator.style.display = 'block'; // Show loading indicator

    const response = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userInput })
    });

    loadingIndicator.style.display = 'none'; // Hide loading indicator

    const data = await response.json();

    chatbox.innerHTML += `<div class="bot-message">${data.text}</div>`;

    if (data.db_empty) {
        const searchButton = document.createElement('button');
        searchButton.className = 'db-empty-button';
        searchButton.innerHTML = '<i class="fab fa-google"></i> Google Search';
        chatbox.appendChild(searchButton);

        // Add event listener to the dynamically created button
        searchButton.addEventListener('click', async () => {
            console.log('Google Search Button Clicked!');
            const loadingIndicator = document.getElementById('loading-indicator');
            loadingIndicator.style.display = 'block'; // Show loading indicator

            const response_search = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: userInput })
            });

            loadingIndicator.style.display = 'none'; // Hide loading indicator

            const data_search = await response_search.json();
            chatbox.innerHTML += `<div class="search-message">${data_search.text}</div>`;
        });
    }
});
