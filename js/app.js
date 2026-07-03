const STORAGE_KEY = 'mallikrasala-transactions';

const form = document.getElementById('transaction-form');
const descriptionInput = document.getElementById('description');
const amountInput = document.getElementById('amount');
const typeInput = document.getElementById('type');
const categoryInput = document.getElementById('category');
const dateInput = document.getElementById('date');
const transactionList = document.getElementById('transaction-list');
const totalIncomeEl = document.getElementById('total-income');
const totalExpenseEl = document.getElementById('total-expense');
const balanceEl = document.getElementById('balance');
const exportBtn = document.getElementById('export-btn');
const clearBtn = document.getElementById('clear-btn');
const categoryChart = document.getElementById('category-chart');

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

function render() {
  transactionList.innerHTML = '';

  const sorted = [...transactions].sort((a, b) => new Date(b.date) - new Date(a.date));

  sorted.forEach((t) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${t.date}</td>
      <td>${t.description}</td>
      <td>${t.category}</td>
      <td>${t.type}</td>
      <td class="${t.type === 'income' ? 'amount-income' : 'amount-expense'}">
        ${t.type === 'income' ? '+' : '-'}${formatCurrency(Math.abs(t.amount))}
      </td>
      <td><button class="delete-btn" data-id="${t.id}">Delete</button></td>
    `;
    transactionList.appendChild(row);
  });

  const totalIncome = transactions
    .filter((t) => t.type === 'income')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalExpense = transactions
    .filter((t) => t.type === 'expense')
    .reduce((sum, t) => sum + t.amount, 0);

  totalIncomeEl.textContent = formatCurrency(totalIncome);
  totalExpenseEl.textContent = formatCurrency(totalExpense);
  balanceEl.textContent = formatCurrency(totalIncome - totalExpense);

  drawCategoryChart();
}

function drawCategoryChart() {
  const ctx = categoryChart.getContext('2d');
  ctx.clearRect(0, 0, categoryChart.width, categoryChart.height);

  const expensesByCategory = {};
  transactions
    .filter((t) => t.type === 'expense')
    .forEach((t) => {
      expensesByCategory[t.category] = (expensesByCategory[t.category] || 0) + t.amount;
    });

  const categories = Object.keys(expensesByCategory);
  if (categories.length === 0) {
    ctx.fillStyle = '#888';
    ctx.font = '14px sans-serif';
    ctx.fillText('No expense data yet', 10, 20);
    return;
  }

  const maxValue = Math.max(...Object.values(expensesByCategory));
  const barWidth = categoryChart.width / categories.length;
  const chartHeight = categoryChart.height - 40;

  categories.forEach((category, i) => {
    const value = expensesByCategory[category];
    const barHeight = (value / maxValue) * chartHeight;
    const x = i * barWidth + 10;
    const y = chartHeight - barHeight + 10;

    ctx.fillStyle = '#1565c0';
    ctx.fillRect(x, y, barWidth - 20, barHeight);

    ctx.fillStyle = '#2b2d42';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(category, x + (barWidth - 20) / 2, chartHeight + 25);
    ctx.fillText(`$${value.toFixed(0)}`, x + (barWidth - 20) / 2, y - 5);
  });
}

form.addEventListener('submit', (e) => {
  e.preventDefault();

  const transaction = {
    id: Date.now().toString(),
    description: descriptionInput.value.trim(),
    amount: Math.abs(parseFloat(amountInput.value)),
    type: typeInput.value,
    category: categoryInput.value,
    date: dateInput.value,
  };

  if (!transaction.description || isNaN(transaction.amount) || transaction.amount <= 0) {
    return;
  }

  transactions.push(transaction);
  saveTransactions();
  render();

  form.reset();
  dateInput.valueAsDate = new Date();
});

transactionList.addEventListener('click', (e) => {
  if (e.target.classList.contains('delete-btn')) {
    const id = e.target.dataset.id;
    transactions = transactions.filter((t) => t.id !== id);
    saveTransactions();
    render();
  }
});

clearBtn.addEventListener('click', () => {
  if (confirm('Delete all transactions? This cannot be undone.')) {
    transactions = [];
    saveTransactions();
    render();
  }
});

exportBtn.addEventListener('click', () => {
  if (transactions.length === 0) return;

  const header = 'Date,Description,Category,Type,Amount\n';
  const rows = transactions
    .map((t) => `${t.date},${t.description},${t.category},${t.type},${t.amount}`)
    .join('\n');

  const blob = new Blob([header + rows], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'mallikrasala-transactions.csv';
  a.click();
  URL.revokeObjectURL(url);
});

render();
