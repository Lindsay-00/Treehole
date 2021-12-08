document.querySelector('form').addEventListener('submit', async function(e) {
    e.preventDefault();
    let response = await fetch('/check?username=' + document.querySelector('input[name=username]').value);
    let available = await response.json();
    if (available) {
        document.querySelector('form').submit();
    }
    else {
        alert('Username is not available');
    }
});