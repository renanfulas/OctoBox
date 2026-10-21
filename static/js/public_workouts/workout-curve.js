/* Curva de evolucao (Cargas) e curva do hero (Inicio) desenhadas no tamanho
   REAL do conteiner.

   O servidor manda um <svg viewBox="0 0 600 140" preserveAspectRatio="none">:
   esticado pra largura do celular, o texto achata e os pontos viram elipses.
   Ele continua sendo o fallback sem JS e a FONTE dos dados -- este script le
   pontos, datas e escala desse SVG ([data-curva-chart]) e redesenha 1:1 em px
   (texto nitido, pontos redondos), com curva monotonica: suave, mas nunca
   inventa pico ou vale entre dois registros. Redesenha no resize; o painel
   Cargas comeca escondido (largura 0), entao o primeiro desenho -- e a
   animacao da linha -- acontece quando ele aparece. */
(function () {
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var kgFormat = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
  var uid = 0;

  function round2(value) {
    return Math.round(value * 100) / 100;
  }

  function svgEl(name, attrs, parent) {
    var node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    if (parent) parent.appendChild(node);
    return node;
  }

  function mapNodes(root, selector, fn) {
    return Array.prototype.map.call(root.querySelectorAll(selector), fn);
  }

  function titleOf(node) {
    var title = node.querySelector('title');
    return title ? title.textContent : '';
  }

  // Fritsch-Carlson: tangentes zeradas onde a inclinacao troca de sinal, entao
  // a curva passa exatamente em cada registro sem extrapolar entre eles.
  function monotonePath(points) {
    var n = points.length;
    if (!n) return '';
    var d = 'M' + round2(points[0][0]) + ',' + round2(points[0][1]);
    if (n === 1) return d;
    var dx = [];
    var slope = [];
    var i;
    for (i = 0; i < n - 1; i += 1) {
      dx[i] = points[i + 1][0] - points[i][0];
      slope[i] = dx[i] ? (points[i + 1][1] - points[i][1]) / dx[i] : 0;
    }
    var tangent = [slope[0]];
    for (i = 1; i < n - 1; i += 1) {
      if (slope[i - 1] * slope[i] <= 0) {
        tangent[i] = 0;
      } else {
        var w1 = 2 * dx[i] + dx[i - 1];
        var w2 = dx[i] + 2 * dx[i - 1];
        tangent[i] = (w1 + w2) / (w1 / slope[i - 1] + w2 / slope[i]);
      }
    }
    tangent[n - 1] = slope[n - 2];
    for (i = 0; i < n - 1; i += 1) {
      var h = dx[i] / 3;
      d += ' C' + round2(points[i][0] + h) + ',' + round2(points[i][1] + h * tangent[i])
        + ' ' + round2(points[i + 1][0] - h) + ',' + round2(points[i + 1][1] - h * tangent[i + 1])
        + ' ' + round2(points[i + 1][0]) + ',' + round2(points[i + 1][1]);
    }
    return d;
  }

  function readChart(svg) {
    var dots = mapNodes(svg, 'circle.workout-load-chart-dot', function (circle) {
      return {
        x: parseFloat(circle.getAttribute('cx')),
        y: parseFloat(circle.getAttribute('cy')),
        version: circle.classList.contains('workout-load-chart-dot--version'),
        title: titleOf(circle),
      };
    });
    if (!dots.length) {
      // O hero manda so a <polyline> (sem pontos nem eixo).
      var line = svg.querySelector('polyline');
      dots = ((line && line.getAttribute('points')) || '').trim().split(/\s+/).filter(Boolean).map(function (pair) {
        var xy = pair.split(',');
        return { x: parseFloat(xy[0]), y: parseFloat(xy[1]), version: false, title: '' };
      });
    }
    dots = dots.filter(function (point) { return isFinite(point.x) && isFinite(point.y); });
    var legacy = mapNodes(svg, 'circle.workout-load-chart-dot--legacy', function (circle) {
      return { x: parseFloat(circle.getAttribute('cx')), y: parseFloat(circle.getAttribute('cy')), title: titleOf(circle) };
    });
    var ticks = mapNodes(svg, 'text.workout-load-chart-label', function (text) {
      return { x: parseFloat(text.getAttribute('x')), text: text.textContent.trim() };
    });
    var scale = mapNodes(svg, 'text.workout-load-chart-scale-label', function (text) {
      // Rotulo vem com {% localize off %} ("92.5 kg"); exibido em pt-BR ("92,5 kg").
      return { y: parseFloat(text.getAttribute('y')), kg: parseFloat(text.textContent) };
    }).filter(function (item) { return isFinite(item.y) && isFinite(item.kg); });
    scale.sort(function (a, b) { return a.y - b.y; });

    var allPoints = dots.concat(legacy);
    var xs = allPoints.map(function (p) { return p.x; }).concat(ticks.map(function (t) { return t.x; }));
    var ys = allPoints.map(function (p) { return p.y; });
    return {
      dots: dots,
      legacy: legacy,
      ticks: ticks,
      maxLabel: scale.length ? kgFormat.format(scale[0].kg) + ' kg' : '',
      minLabel: scale.length > 1 ? kgFormat.format(scale[scale.length - 1].kg) + ' kg' : '',
      x0: Math.min.apply(null, xs),
      x1: Math.max.apply(null, xs),
      y0: scale.length ? scale[0].y : Math.min.apply(null, ys),
      y1: scale.length ? scale[scale.length - 1].y : Math.max.apply(null, ys),
      label: svg.getAttribute('aria-label') || '',
    };
  }

  function animateDraw(paths) {
    paths.forEach(function (path) {
      var length = path.getTotalLength();
      path.style.strokeDasharray = String(length);
      path.style.strokeDashoffset = String(length);
      path.getBoundingClientRect();
      path.classList.add('is-drawing');
      window.requestAnimationFrame(function () { path.style.strokeDashoffset = '0'; });
    });
  }

  function paint(host, data, withAxis) {
    var width = host.clientWidth;
    var height = host.clientHeight;
    if (!width || !height || !data.dots.length) return;

    // O hero nao tem eixo: a curva ocupa a largura toda (dominio so dos pontos).
    var xs = data.dots.map(function (p) { return p.x; });
    var ys = data.dots.map(function (p) { return p.y; });
    var x0 = withAxis ? data.x0 : Math.min.apply(null, xs);
    var x1 = withAxis ? data.x1 : Math.max.apply(null, xs);
    var y0 = withAxis ? data.y0 : Math.min.apply(null, ys);
    var y1 = withAxis ? data.y1 : Math.max.apply(null, ys);
    var padLeft = 8;
    var padRight = 12;
    var padTop = withAxis ? 26 : 10;
    var padBottom = withAxis ? 28 : 10;
    function sx(x) { return padLeft + ((x - x0) / ((x1 - x0) || 1)) * (width - padLeft - padRight); }
    function sy(y) { return padTop + ((y - y0) / ((y1 - y0) || 1)) * (height - padTop - padBottom); }
    var baseline = withAxis ? sy(y1) : height;
    var points = data.dots.map(function (p) { return [sx(p.x), sy(p.y)]; });
    var id = 'workout-curve-' + (uid += 1);

    var svg = svgEl('svg', { viewBox: '0 0 ' + width + ' ' + height, width: width, height: height, role: 'img', 'aria-label': data.label });
    var defs = svgEl('defs', {}, svg);
    var gradient = svgEl('linearGradient', { id: id + '-area', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    svgEl('stop', { offset: '0%', class: 'workout-curve__area-start' }, gradient);
    svgEl('stop', { offset: '100%', class: 'workout-curve__area-end' }, gradient);
    var blur = svgEl('filter', { id: id + '-blur', x: '-10%', y: '-60%', width: '120%', height: '220%' }, defs);
    svgEl('feGaussianBlur', { stdDeviation: 3.5 }, blur);

    if (withAxis) {
      var topY = sy(y0);
      svgEl('line', { class: 'workout-curve__guide', x1: padLeft, x2: width - padRight, y1: topY, y2: topY }, svg);
      svgEl('line', { class: 'workout-curve__guide', x1: padLeft, x2: width - padRight, y1: baseline, y2: baseline }, svg);
      if (data.maxLabel) svgEl('text', { x: padLeft, y: topY - 8 }, svg).textContent = data.maxLabel;
      if (data.minLabel) svgEl('text', { x: padLeft, y: baseline - 8 }, svg).textContent = data.minLabel;
      data.ticks.forEach(function (tick, index) {
        var anchor = index === 0 ? 'start' : (index === data.ticks.length - 1 ? 'end' : 'middle');
        var x = Math.min(Math.max(sx(tick.x), padLeft), width - padRight);
        svgEl('text', { x: x, y: height - 6, 'text-anchor': anchor }, svg).textContent = tick.text;
      });
      data.dots.forEach(function (dot) {
        if (dot.version) svgEl('line', { class: 'workout-curve__guide', x1: sx(dot.x), x2: sx(dot.x), y1: topY, y2: baseline }, svg);
      });
    }

    var d = monotonePath(points);
    var last = points[points.length - 1];
    if (points.length > 1) {
      svgEl('path', {
        class: 'workout-curve__area',
        d: d + ' L' + round2(last[0]) + ',' + round2(baseline) + ' L' + round2(points[0][0]) + ',' + round2(baseline) + ' Z',
        fill: 'url(#' + id + '-area)',
      }, svg);
    }
    var glow = svgEl('path', { class: 'workout-curve__glow', d: d, filter: 'url(#' + id + '-blur)' }, svg);
    var core = svgEl('path', { class: 'workout-curve__line', d: d }, svg);

    if (withAxis) {
      data.legacy.forEach(function (point) {
        var circle = svgEl('circle', { class: 'workout-curve__dot workout-curve__dot--legacy', cx: sx(point.x), cy: sy(point.y), r: 3 }, svg);
        if (point.title) svgEl('title', {}, circle).textContent = point.title;
      });
      data.dots.slice(0, -1).forEach(function (dot) {
        var circle = svgEl('circle', {
          class: 'workout-curve__dot' + (dot.version ? ' workout-curve__dot--version' : ''),
          cx: sx(dot.x), cy: sy(dot.y), r: 3.25,
        }, svg);
        if (dot.title) svgEl('title', {}, circle).textContent = dot.title;
      });
    }
    // Ultimo registro = o pico atual da curva.
    svgEl('circle', { class: 'workout-curve__peak-halo', cx: last[0], cy: last[1], r: 10, filter: 'url(#' + id + '-blur)' }, svg);
    svgEl('circle', { class: 'workout-curve__peak', cx: last[0], cy: last[1], r: 4.5 }, svg);

    host.replaceChildren(svg);

    if (!host.hasAttribute('data-curve-drawn')) {
      host.setAttribute('data-curve-drawn', '');
      if (!reduceMotion && points.length > 1) animateDraw([glow, core]);
    }
  }

  function enhance(source) {
    var withAxis = source.getAttribute('data-curva-chart') === 'axis';
    var data = readChart(source);
    if (data.dots.length < 2) return;
    var host = document.createElement('div');
    host.className = 'workout-curve workout-curve--' + (withAxis ? 'axis' : 'hero');
    source.replaceWith(host);

    var frame = 0;
    var observer = null;
    function schedule() {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(function () {
        try {
          paint(host, data, withAxis);
        } catch (error) {
          // Devolve o SVG do servidor: o grafico nunca some por erro aqui.
          if (observer) observer.disconnect();
          window.removeEventListener('resize', schedule);
          host.replaceWith(source);
          if (window.console) window.console.warn('workout-curve: mantendo o grafico do servidor', error);
        }
      });
    }
    if ('ResizeObserver' in window) {
      observer = new ResizeObserver(schedule);
      observer.observe(host);
    } else {
      window.addEventListener('resize', schedule);
      schedule();
    }
  }

  document.querySelectorAll('svg[data-curva-chart]').forEach(function (svg) {
    try {
      enhance(svg);
    } catch (error) {
      // Falhou antes de trocar: o SVG do servidor continua no lugar.
      if (window.console) window.console.warn('workout-curve: mantendo o grafico do servidor', error);
    }
  });
})();
