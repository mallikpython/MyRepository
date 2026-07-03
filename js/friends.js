const STORAGE_KEY = 'mallikrasala-friend-transactions';

const form = document.getElementById('friend-form');
const personInput = document.getElementById('person');
const amountInput = document.getElementById('amount');
const directionInput = document.getElementById('direction');
const mediumInput = document.getElementById('medium');
const dateInput = document.getElementById('date');
const noteInput = document.getElementById('note');
const friendList = document.getElementById('friend-list');
const personSummary = document.getElementById('person-summary');
const totalGivenEl = document.getElementById('total-given');
const totalReceivedEl = document.getElementById('total-received');
const outstandingEl = document.getElementById('outstanding');
const exportBtn = document.getElementById('export-btn');
const clearBtn = document.getElementById('clear-btn');

let transactions = loadTransactions();

dateInput.valueAsDate = new Date();

function loadTransactions() {
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

function saveTransactions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(transactions));
}

function formatCurrency(value) {
  return `$${value.toFixed(2)}`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function render() {
  friendList.innerHTML = '';

  const sorted = [...transactions].sort((a, b) => new Date(b.date) - new Date(a.date));

  sorted.forEach((t) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${t.date}</td>
      <td>${escapeHtml(t.person)}</td>
      <td>${t.direction === 'given' ? 'Given' : 'Received back'}</td>
      <td>${escapeHtml(t.medium)}</td>
      <td>${escapeHtml(t.note || '')}</td>
      <td class="${t.direction === 'given' ? 'amount-expense' : 'amount-income'}">
        ${t.direction === 'given' ? '-' : '+'}${formatCurrency(t.amount)}
      </td>
      <td><button class="delete-btn" data-id="${t.id}">Delete</button></td>
    `;
    friendList.appendChild(row);
  });

  const totalGiven = transactions
    .filter((t) => t.direction === 'given')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalReceived = transactions
    .filter((t) => t.direction === 'received')
    .reduce((sum, t) => sum + t.amount, 0);

  totalGivenEl.textContent = formatCurrency(totalGiven);
  totalReceivedEl.textContent = formatCurrency(totalReceived);
  outstandingEl.textContent = formatCurrency(totalGiven - totalReceived);

  renderPersonSummary();
}

function renderPersonSummary() {
  const byPerson = {};
  transactions.forEach((t) => {
    if (!byPerson[t.person]) {
      byPerson[t.person] = { given: 0, received: 0 };
    }
    byPerson[t.person][t.direction === 'given' ? 'given' : 'received'] += t.amount;
  });

  personSummary.innerHTML = '';
  Object.keys(byPerson)
    .sort((a, b) => {
      const outA = byPerson[a].given - byPerson[a].received;
      const outB = byPerson[b].given - byPerson[b].received;
      return outB - outA;
    })
    .forEach((person) => {
      const { given, received } = byPerson[person];
      const outstanding = given - received;
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${escapeHtml(person)}</td>
        <td class="amount-expense">${formatCurrency(given)}</td>
        <td class="amount-income">${formatCurrency(received)}</td>
        <td class="${outstanding > 0 ? 'amount-expense' : 'amount-income'}">${formatCurrency(outstanding)}</td>
      `;
      personSummary.appendChild(row);
    });
}

form.addEventListener('submit', (e) => {
  e.preventDefault();

  const transaction = {
    id: Date.now().toString(),
    person: personInput.value.trim(),
    amount: Math.abs(parseFloat(amountInput.value)),
    direction: directionInput.value,
    medium: mediumInput.value,
    date: dateInput.value,
    note: noteInput.value.trim(),
  };

  if (!transaction.person || isNaN(transaction.amount) || transaction.amount <= 0) {
    return;
  }

  transactions.push(transaction);
  saveTransactions();
  render();

  form.reset();
  dateInput.valueAsDate = new Date();
});

friendList.addEventListener('click', (e) => {
  if (e.target.classList.contains('delete-btn')) {
    const id = e.target.dataset.id;
    transactions = transactions.filter((t) => t.id !== id);
    saveTransactions();
    render();
  }
});

clearBtn.addEventListener('click', () => {
  if (confirm('Delete all friends & family transactions? This cannot be undone.')) {
    transactions = [];
    saveTransactions();
    render();
  }
});

exportBtn.addEventListener('click', () => {
  if (transactions.length === 0) return;

  const escapeCsv = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const header = 'Date,Person,Direction,Medium,Note,Amount\n';
  const rows = transactions
    .map((t) =>
      [t.date, t.person, t.direction, t.medium, t.note || '', t.amount].map(escapeCsv).join(',')
    )
    .join('\n');

  const blob = new Blob([header + rows], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'friends-family-transactions.csv';
  a.click();
  URL.revokeObjectURL(url);
});

render();
