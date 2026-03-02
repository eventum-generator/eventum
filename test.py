import time

from jinja2 import DictLoader, Environment

N = 1_000_000

tmpl = '{"@timestamp": ""}'
env = Environment(loader=DictLoader({'t.jinja': tmpl}))
template = env.get_template('t.jinja')

start = time.monotonic()
for _ in range(N):
    template.render()
dur = time.monotonic() - start
print(f'Simple variable:  {N / dur:,.0f} EPS ({dur:.1f}s)')
