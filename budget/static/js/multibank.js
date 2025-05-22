document.addEventListener('DOMContentLoaded', function() {
    // アコーディオンの開閉機能
    const sectionHeaders = document.querySelectorAll('.section-header');
    sectionHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const target = document.getElementById(targetId);
            if (target) {
                target.classList.toggle('show');
                this.setAttribute('aria-expanded', target.classList.contains('show'));
            }
        });
    });

    // すべて開くボタン
    const openAllButton = document.querySelector('button[onclick="openAllDetails()"]');
    if (openAllButton) {
        openAllButton.addEventListener('click', function() {
            document.querySelectorAll('.collapse').forEach(element => {
                element.classList.add('show');
            });
            document.querySelectorAll('.section-header').forEach(header => {
                header.setAttribute('aria-expanded', 'true');
            });
        });
    }

    // すべて閉じるボタン
    const closeAllButton = document.querySelector('button[onclick="closeAllDetails()"]');
    if (closeAllButton) {
        closeAllButton.addEventListener('click', function() {
            document.querySelectorAll('.collapse').forEach(element => {
                element.classList.remove('show');
            });
            document.querySelectorAll('.section-header').forEach(header => {
                header.setAttribute('aria-expanded', 'false');
            });
        });
    }

    // 金額のフォーマット
    formatAmounts();
});

function formatAmounts() {
    // 金額のフォーマット
    document.querySelectorAll('.text-right').forEach(cell => {
        const amount = cell.textContent.trim();
        if (amount && !isNaN(amount)) {
            cell.textContent = new Intl.NumberFormat('ja-JP').format(parseInt(amount));
        }
    });
}

// すべてのセクションを開く
function openAllSections() {
    document.querySelectorAll('.collapse').forEach(section => {
        section.classList.add('show');
    });
}

// すべてのセクションを閉じる
function closeAllSections() {
    document.querySelectorAll('.collapse').forEach(section => {
        section.classList.remove('show');
    });
} 