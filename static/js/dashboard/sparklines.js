// Lightweight sparkline loader and KPI selector
(function(){
    function renderSparkline(el, points){
        if(!points || points.length===0) return;
        var w = el.clientWidth || 64;
        var h = el.clientHeight || 28;
        var max = Math.max.apply(null, points);
        var min = Math.min.apply(null, points);
        var range = max - min || 1;
        var step = w / (points.length - 1);
        var d = points.map(function(p,i){
            var x = Math.round(i * step);
            var y = Math.round(h - ((p - min) / range) * h);
            return x + "," + y;
        }).join(' L ');
        var svg = '<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
                +'<polyline fill="none" stroke="currentColor" stroke-width="1.6" points="'+d+'" />'
                +'</svg>';
        el.innerHTML = svg;
    }

    function initSparklines(){
        var els = document.querySelectorAll('.metric-spark[data-spark]');
        els.forEach(function(el){
            try{
                var raw = el.getAttribute('data-spark');
                var points = JSON.parse(raw);
                renderSparkline(el, points);
            }catch(e){
                try{
                    var arr = (el.getAttribute('data-spark')||'').split(',').map(Number);
                    renderSparkline(el, arr);
                }catch(e){}
            }
        });
    }

    function initKpiSelector(){
        var sel = document.getElementById('kpi-selector');
        if(!sel) return;
        // restore selection
        var saved = localStorage.getItem('dashboard.kpi.selected');
        if(saved) sel.value = saved;
        sel.addEventListener('change', function(){
            var v = sel.value;
            localStorage.setItem('dashboard.kpi.selected', v);
            var container = document.querySelector('.dashboard-summary-topline');
            if(!container) return;
            var card = container.querySelector('[data-metric-id="'+v+'"]');
            if(card){
                container.insertBefore(card, container.firstChild);
            }
        });
        // trigger once
        sel.dispatchEvent(new Event('change'));
    }

    if('requestIdleCallback' in window){
        requestIdleCallback(function(){ initSparklines(); initKpiSelector(); });
    } else {
        window.addEventListener('DOMContentLoaded', function(){ setTimeout(function(){ initSparklines(); initKpiSelector(); },50); });
    }
})();
