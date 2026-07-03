# Mallik Rasala - Personal Finance

A simple personal finance tracker that runs entirely in your browser. Track income and expenses, view your balance, and see a breakdown of spending by category. All data is stored locally using the browser's `localStorage` — nothing is sent to a server.

## Running locally

No build tools or dependencies required. From the project root, start any static file server, for example:

```bash
python3 -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Features

- Add income and expense transactions with description, amount, category, and date
- Live summary of total income, expenses, and balance
- Bar chart breakdown of spending by category
- Export transaction history to CSV
- Clear all data
