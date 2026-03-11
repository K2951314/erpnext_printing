const HTML2CANVAS_SRC =
    'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';

const isPrintPage = () => {
    const path = window.location.pathname || '';
    if (path.includes('/printview') || path.endsWith('/print')) {
        return true;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get('print') === '1' || params.get('print') === 'true') {
        return true;
    }

    return params.has('doctype') && params.has('name') && params.has('format');
};

const loadHtml2Canvas = () => {
    if (!isPrintPage()) {
        return;
    }

    if (window.html2canvas) {
        return;
    }

    const existingScript = Array.from(document.scripts).find(
        (script) => script.src === HTML2CANVAS_SRC
    );
    if (existingScript) {
        return;
    }

    const script = document.createElement('script');
    script.src = HTML2CANVAS_SRC;
    script.onload = () => console.log('html2canvas loaded');
    document.head.appendChild(script);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadHtml2Canvas);
} else {
    loadHtml2Canvas();
}
