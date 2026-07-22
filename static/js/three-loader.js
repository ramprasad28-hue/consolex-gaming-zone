/* ============================================================
   CONSOLEX — three-loader.js
   3D Gaming-themed loading screen
   Shows on page load, fades out when ready
   ============================================================ */

(function () {
    'use strict';

    /* Don't show if user prefers reduced motion */
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* Create loader HTML */
    const loader = document.createElement('div');
    loader.id = 'consolex-loader';
    loader.innerHTML = `
        <div class="cl-inner">
            <div class="cl-ps5">
                <div class="cl-ps5-body"></div>
                <div class="cl-ps5-wing cl-ps5-wing-l"></div>
                <div class="cl-ps5-wing cl-ps5-wing-r"></div>
                <div class="cl-ps5-led"></div>
            </div>
            <div class="cl-rings">
                <div class="cl-ring cl-ring-1"></div>
                <div class="cl-ring cl-ring-2"></div>
                <div class="cl-ring cl-ring-3"></div>
            </div>
            <div class="cl-text">
                <span class="cl-logo">CONSOLEX</span>
                <div class="cl-bar">
                    <div class="cl-bar-fill"></div>
                </div>
                <span class="cl-status">Loading Experience</span>
            </div>
        </div>
    `;

    /* Inject styles */
    const style = document.createElement('style');
    style.textContent = `
        #consolex-loader {
            position: fixed;
            inset: 0;
            z-index: 99999;
            background: #080810;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.6s ease, visibility 0.6s ease;
        }
        #consolex-loader.cl-hide {
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }
        .cl-inner {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 32px;
        }

        /* PS5 mini model */
        .cl-ps5 {
            position: relative;
            width: 60px;
            height: 90px;
            animation: clFloat 2.5s ease-in-out infinite;
        }
        .cl-ps5-body {
            position: absolute;
            inset: 0;
            background: #111118;
            border-radius: 8px 8px 6px 6px;
            border: 1px solid rgba(255,255,255,0.06);
        }
        .cl-ps5-wing {
            position: absolute;
            width: 4px;
            height: 82px;
            background: #d8d8e0;
            border-radius: 3px;
            top: 4px;
        }
        .cl-ps5-wing-l { left: -2px; }
        .cl-ps5-wing-r { right: -2px; }
        .cl-ps5-led {
            position: absolute;
            bottom: 18px;
            left: 50%;
            transform: translateX(-50%);
            width: 2px;
            height: 24px;
            background: #00f0ff;
            border-radius: 2px;
            box-shadow: 0 0 8px #00f0ff, 0 0 20px #00f0ff;
            animation: clLedPulse 1.2s ease-in-out infinite;
        }

        /* Spinning rings */
        .cl-rings {
            position: absolute;
            width: 120px;
            height: 120px;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        .cl-ring {
            position: absolute;
            inset: 0;
            border-radius: 50%;
            border: 2px solid transparent;
        }
        .cl-ring-1 {
            border-top-color: rgba(0, 240, 255, 0.5);
            animation: clSpin 1.8s linear infinite;
        }
        .cl-ring-2 {
            inset: 12px;
            border-right-color: rgba(191, 0, 255, 0.4);
            animation: clSpin 2.4s linear infinite reverse;
        }
        .cl-ring-3 {
            inset: 24px;
            border-bottom-color: rgba(255, 107, 0, 0.3);
            animation: clSpin 3s linear infinite;
        }

        /* Text */
        .cl-text {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 14px;
        }
        .cl-logo {
            font-family: 'Orbitron', monospace;
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: 6px;
            color: #fff;
            text-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
        }
        .cl-bar {
            width: 160px;
            height: 3px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            overflow: hidden;
        }
        .cl-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #00f0ff, #bf00ff);
            border-radius: 3px;
            animation: clProgress 2.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        .cl-status {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: rgba(154, 157, 184, 0.7);
        }

        @keyframes clFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }
        @keyframes clLedPulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 8px #00f0ff, 0 0 20px #00f0ff; }
            50% { opacity: 0.5; box-shadow: 0 0 4px #00f0ff; }
        }
        @keyframes clSpin {
            to { transform: rotate(360deg); }
        }
        @keyframes clProgress {
            0% { width: 0%; }
            30% { width: 45%; }
            60% { width: 70%; }
            100% { width: 100%; }
        }
    `;

    document.head.appendChild(style);

    if (prefersReduced) {
        loader.style.display = 'none';
    } else {
        document.body.prepend(loader);
    }

    /* Hide loader when page is ready */
    function hideLoader() {
        loader.classList.add('cl-hide');
        setTimeout(() => loader.remove(), 700);
    }

    if (prefersReduced) {
        /* do nothing — loader never shown */
    } else if (document.readyState === 'complete') {
        setTimeout(hideLoader, 400);
    } else {
        window.addEventListener('load', () => setTimeout(hideLoader, 400));
    }

    /* Fallback: force hide after 4 seconds max */
    setTimeout(() => {
        if (loader.parentNode) hideLoader();
    }, 4000);

}());
