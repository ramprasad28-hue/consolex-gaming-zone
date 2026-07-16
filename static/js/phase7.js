/* ============================================================
   CONSOLEX — phase7.js
   Handles: FAQ accordion
   (scroll-reveal for [data-reveal] is already handled globally
   by phase4_6.js — no need to duplicate it here)
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

    var faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(function (item) {
        var btn = item.querySelector('.faq-q');
        var answer = item.querySelector('.faq-a');
        if (!btn || !answer) return;

        btn.addEventListener('click', function () {
            var isOpen = btn.getAttribute('aria-expanded') === 'true';

            // Close all other items (single-open accordion)
            faqItems.forEach(function (other) {
                if (other === item) return;
                var otherBtn = other.querySelector('.faq-q');
                var otherAnswer = other.querySelector('.faq-a');
                otherBtn.setAttribute('aria-expanded', 'false');
                otherAnswer.style.maxHeight = null;
            });

            btn.setAttribute('aria-expanded', String(!isOpen));
            answer.style.maxHeight = isOpen ? null : answer.scrollHeight + 'px';
        });
    });

});
