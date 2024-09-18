// static/main.js
document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    socket.on('update_data', function (data) {
        console.log('Received data:', data);
        const tableBody = document.getElementById('data-body');
        tableBody.innerHTML = '';

        if (Array.isArray(data) && data.length > 0) {
            console.log('Properties of the first item:', Object.keys(data[0]));
        }

        data.forEach((item) => {
            const row = document.createElement('tr');
            const propertiesToShow = ['symbol', 'bid_price', 'ask_price', 'volume' , 'quote_volume'];

            propertiesToShow.forEach((prop) => {
                const cell = document.createElement('td');
                cell.textContent = item[prop];
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    });
});

