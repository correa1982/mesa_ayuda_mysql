
function getSensitiveSignaturePadOptions(overrides) {
  return Object.assign({
    minWidth: 0.3,
    maxWidth: 3.5,
    dotSize: 2.0,
    throttle: 0,
    minDistance: 0,
    velocityFilterWeight: 0.15,
    penColor: '#111827',
    backgroundColor: '#ffffff'
  }, overrides || {});
}

window.getSensitiveSignaturePadOptions = getSensitiveSignaturePadOptions;

function SignaturePadSimple(id, overrides){
  const canvas = document.getElementById(id);
  if (!canvas) {
    throw new Error('No se encontro el canvas de firma: ' + id);
  }

  const logicalWidth = parseInt(canvas.getAttribute('width') || canvas.clientWidth || 480, 10);
  const logicalHeight = parseInt(canvas.getAttribute('height') || canvas.clientHeight || 160, 10);
  const options = getSensitiveSignaturePadOptions(overrides);

  function setupCanvas() {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    canvas.width = Math.floor(logicalWidth * ratio);
    canvas.height = Math.floor(logicalHeight * ratio);
    canvas.style.width = logicalWidth + 'px';
    canvas.style.height = logicalHeight + 'px';
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.fillStyle = options.backgroundColor;
    context.fillRect(0, 0, logicalWidth, logicalHeight);
    return context;
  }

  if (typeof window.SignaturePad === 'function') {
    setupCanvas();
    const pad = new window.SignaturePad(canvas, options);
    pad.clear();

    return {
      toDataURL: () => pad.toDataURL('image/png'),
      clear: () => pad.clear(),
      isBlank: () => pad.isEmpty(),
      instance: pad
    };
  }

  const context = setupCanvas();
  let drawing = false;
  let lastPoint = null;
  let hasDrawn = false;

  context.lineWidth = 2.0;
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.strokeStyle = options.penColor;
  context.fillStyle = options.penColor;

  function getPoint(event) {
    const rect = canvas.getBoundingClientRect();
    const source = event.touches && event.touches[0]
      ? event.touches[0]
      : event.changedTouches && event.changedTouches[0]
        ? event.changedTouches[0]
        : event;

    return {
      x: source.clientX - rect.left,
      y: source.clientY - rect.top
    };
  }

  function drawDot(point) {
    context.beginPath();
    context.arc(point.x, point.y, Math.max(options.minWidth, options.dotSize) / 2, 0, Math.PI * 2);
    context.fill();
    hasDrawn = true;
  }

  function drawLine(from, to) {
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
    hasDrawn = true;
  }

  function start(event) {
    event.preventDefault();
    drawing = true;
    lastPoint = getPoint(event);
    drawDot(lastPoint);
  }

  function move(event) {
    if (!drawing) {
      return;
    }
    event.preventDefault();
    const point = getPoint(event);
    drawLine(lastPoint, point);
    lastPoint = point;
  }

  function end(event) {
    if (event) {
      event.preventDefault();
    }
    drawing = false;
    lastPoint = null;
  }

  if (window.PointerEvent) {
    canvas.addEventListener('pointerdown', start);
    canvas.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
  } else {
    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', move);
    window.addEventListener('mouseup', end);
    canvas.addEventListener('touchstart', start, { passive: false });
    canvas.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', end, { passive: false });
    window.addEventListener('touchcancel', end, { passive: false });
  }

  return {
    toDataURL: () => canvas.toDataURL('image/png'),
    clear: () => {
      context.clearRect(0, 0, logicalWidth, logicalHeight);
      context.fillStyle = options.backgroundColor;
      context.fillRect(0, 0, logicalWidth, logicalHeight);
      context.fillStyle = options.penColor;
      hasDrawn = false;
    },
    isBlank: () => !hasDrawn
  };
}

window.SignaturePadSimple = SignaturePadSimple;
