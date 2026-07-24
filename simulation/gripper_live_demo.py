#!/usr/bin/env python3
"""Run the EGP simulator and open a small live telemetry dashboard."""

import argparse
import json
import subprocess
import sys
import threading
import urllib.request
import ssl
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from simulate_gripper import encode_id, token


HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><title>EGP Gripper Live Data</title>
<style>
body{margin:0;background:#101827;color:#e8eef8;font:15px system-ui,sans-serif}main{max-width:1100px;margin:24px auto;padding:0 18px}h1{margin:0 0 6px}.muted{color:#91a4bf}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.card{background:#19263a;border:1px solid #2d405d;border-radius:10px;padding:14px}.label{color:#91a4bf;font-size:12px}.value{font-size:25px;font-weight:700;margin-top:5px}.state{color:#5ee6a8}.charts{display:grid;grid-template-columns:1fr 1fr;gap:14px}.chart{background:#19263a;border:1px solid #2d405d;border-radius:10px;padding:12px}.chart h3{margin:0 0 8px;font-size:14px}.chart canvas{width:100%;height:180px}.error{color:#ff8c8c}@media(max-width:750px){.grid,.charts{grid-template-columns:1fr 1fr}}
</style></head><body><main>
<h1>EGP Gripper — live telemetry</h1><div class="muted">IDTA 02008-1-1 Time Series · polling every 1 second</div>
<div id="error" class="error"></div><section class="grid">
<div class="card"><div class="label">STATE</div><div id="state" class="value state">—</div></div>
<div class="card"><div class="label">JAW POSITION</div><div id="position" class="value">—</div></div>
<div class="card"><div class="label">GRIP FORCE</div><div id="force" class="value">—</div></div>
<div class="card"><div class="label">CYCLES</div><div id="cycles" class="value">—</div></div></section>
<section class="charts"><div class="chart"><h3>Jaw position (mm)</h3><canvas id="positionChart"></canvas></div>
<div class="chart"><h3>Grip force (N)</h3><canvas id="forceChart"></canvas></div>
<div class="chart"><h3>Temperature (°C)</h3><canvas id="temperatureChart"></canvas></div>
<div class="chart"><h3>Motor current (A)</h3><canvas id="currentChart"></canvas></div></section>
<p class="muted">Last sample: <span id="updated">—</span></p></main>
<script>
const series={position:[],force:[],temperature:[],current:[]};
function draw(id,data,color){const c=document.getElementById(id),d=devicePixelRatio||1,r=c.getBoundingClientRect();c.width=r.width*d;c.height=r.height*d;const x=c.getContext('2d');x.scale(d,d);const w=r.width,h=r.height;x.clearRect(0,0,w,h);x.strokeStyle='#2d405d';x.lineWidth=1;for(let i=1;i<5;i++){x.beginPath();x.moveTo(0,h*i/5);x.lineTo(w,h*i/5);x.stroke()}if(data.length<2)return;const lo=Math.min(...data),hi=Math.max(...data),span=hi-lo||1;x.strokeStyle=color;x.lineWidth=2;x.beginPath();data.forEach((v,i)=>{const px=i*(w-8)/(data.length-1)+4,py=h-4-(v-lo)*(h-8)/span;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke()}
async function refresh(){try{const r=await fetch('/api/data',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const v=await r.json();document.getElementById('error').textContent='';for(const [id,val] of [['state',v.CurrentState],['position',v.JawPosition+' mm'],['force',v.GripForce+' N'],['cycles',v.CycleCount]])document.getElementById(id).textContent=val;document.getElementById('updated').textContent=new Date(v.SampleTime).toLocaleTimeString();for(const [k,n] of [['position','JawPosition'],['force','GripForce'],['temperature','Temperature'],['current','MotorCurrent']]){series[k].push(Number(v[n]));if(series[k].length>60)series[k].shift()}draw('positionChart',series.position,'#57b7ff');draw('forceChart',series.force,'#5ee6a8');draw('temperatureChart',series.temperature,'#ffbe5c');draw('currentChart',series.current,'#ff7f9f')}catch(e){document.getElementById('error').textContent='Connection error: '+e.message}}refresh();setInterval(refresh,1000);addEventListener('resize',refresh);
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = HTML.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path == "/api/data":
            try:
                body = json.dumps(self.server.read_data()).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception as exc:
                body = str(exc).encode(); self.send_response(502); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        self.send_error(404)
    def log_message(self, *_): pass


def read_data(server, bearer):
    url = f"{server}/submodels/{encode_id('https://example.org/submodels/schunk/egp-40-n-n-b/timeseries')}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
    with urllib.request.urlopen(req, timeout=10, context=ssl._create_unverified_context()) as response:
        model = json.loads(response.read())
    segments = next(x for x in model["submodelElements"] if x["idShort"] == "Segments")["value"]
    internal = next(x for x in segments if x["idShort"] == "InternalSegment")
    records = next(x for x in internal["value"] if x["idShort"] == "Records")["value"]
    record = records[-1]
    values = {x["idShort"]: x.get("value") for x in record["value"]}
    for k in ["JawPosition", "GripForce", "Temperature", "MotorCurrent"]: values[k] = float(values[k])
    values["CycleCount"] = int(values["CycleCount"]); values["SampleTime"] = int(__import__("time").time() * 1000)
    return values


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--server", default="https://172.17.255.202"); parser.add_argument("--port", type=int, default=8765); parser.add_argument("--no-browser", action="store_true"); args = parser.parse_args()
    bearer = token(args.server.rstrip("/"), "basyx-admin", "basyx-admin")
    simulator_script = Path(__file__).with_name("simulate_timeseries.py")
    simulator = subprocess.Popen([sys.executable, str(simulator_script), "--server", args.server, "--interval", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler); httpd.read_data = lambda: read_data(args.server.rstrip("/"), bearer)
    print(f"Dashboard: http://127.0.0.1:{args.port}"); print(f"Simulator PID: {simulator.pid}")
    if not args.no_browser: threading.Timer(0.5, lambda: webbrowser.open_new(f"http://127.0.0.1:{args.port}")).start()
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: simulator.terminate(); httpd.server_close()


if __name__ == "__main__": main()
