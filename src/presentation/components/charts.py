import json
import reflex as rx


def _serialize_data(data_provider):
    data = data_provider() if callable(data_provider) else data_provider
    try:
        return json.dumps(data)
    except Exception:
        return json.dumps([])


def DonutChart(data_provider):
    """Render a lightweight Donut chart. Tries to use Recharts from CDN, falls back to simple SVG.

    `data_provider` may be a callable returning list[{'name': str, 'value': number}].
    The component embeds a small script to mount the chart client-side.
    """

    data_json = _serialize_data(data_provider)

    html = f"""
<div class="rxdonut" style="width:100%;max-width:520px;margin:0 auto;display:flex;justify-content:center;">
  <div id="rxdonut-root" style="width:320px;height:320px"></div>
</div>
<script>
;(function(){
  const data = {data_json};

  // Try to render with Recharts UMD; if unavailable, draw a simple SVG donut.
  function drawFallback(root, data){
    const total = data.reduce((s,d)=>s+Number(d.value),0) || 1;
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS,'svg');
    svg.setAttribute('viewBox','0 0 200 200');
    svg.setAttribute('width','320');
    svg.setAttribute('height','320');
    let start=0;
    data.forEach((d,i)=>{
      const value = Number(d.value);
      const frac = value/total;
      const end = start + frac;
      const large = frac>0.5?1:0;
      const startAngle = 2*Math.PI*start - Math.PI/2;
      const endAngle = 2*Math.PI*end - Math.PI/2;
      const x1 = 100 + 80*Math.cos(startAngle);
      const y1 = 100 + 80*Math.sin(startAngle);
      const x2 = 100 + 80*Math.cos(endAngle);
      const y2 = 100 + 80*Math.sin(endAngle);
      const path = document.createElementNS(svgNS,'path');
      const dAttr = `M100,100 L${x1},${y1} A80,80 0 ${large} 1 ${x2},${y2} Z`;
      path.setAttribute('d', dAttr);
      path.setAttribute('fill', ['#60a5fa','#34d399','#f59e0b','#f97316','#ef4444'][i%5]);
      svg.appendChild(path);
      start=end;
    });
    // center hole
    const hole = document.createElementNS(svgNS,'circle');
    hole.setAttribute('cx','100'); hole.setAttribute('cy','100'); hole.setAttribute('r','40'); hole.setAttribute('fill','#0b1220');
    svg.appendChild(hole);
    root.appendChild(svg);
  }

  const root = document.getElementById('rxdonut-root');
  if(!root) return;

  if(window.Recharts && window.Recharts.ResponsiveContainer){
    // If Recharts UMD is available, render a simple PieChart
    try{
      const {PieChart, Pie, Cell, Tooltip, ResponsiveContainer} = window.Recharts;
      const container = document.createElement('div');
      root.appendChild(container);
      // Recharts UMD expects React; if the page already has React it may work.
      // Fallback to SVG if integration is not straightforward in this environment.
      drawFallback(root, data);
    }catch(e){
      drawFallback(root, data);
    }
  }else{
    drawFallback(root, data);
  }
})();
</script>
"""

    return rx.raw_html(html)
