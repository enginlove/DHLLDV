"""
SystemTab: Create the tab with the system (pipeline and pumps) information

Execute by running 'bokeh serve --show .\Scripts\bokeh_viewer.py' to open a tab in your browser

Added by R. Ramsdell 01 September, 2021
"""
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, TextInput, Button, RadioButtonGroup
from bokeh.models import Spacer, Div, Panel, Tabs, LinearAxis, Range1d
from bokeh.plotting import figure

from DHLLDV.PipeObj import Pipeline

pipeline = Pipeline()

flow_list = [pipeline.pipesections[-1].flow(v) for v in pipeline.slurry.vls_list]
im_source = ColumnDataSource(data=dict(Q=flow_list,
                                       im=[pipeline.calc_system_head(Q)[0] for Q in flow_list],
                                       il=[pipeline.calc_system_head(Q)[1] for Q in flow_list],
                                       ))

HQ_TOOLTIPS = [('name', "$name"),
               ("Flow (m\u00b3/sec)", "@Q"),
               ("Slurry Graded Cvt=c (m/m)", "@im"),
               ("Fluid (m/m)", "@il"),
              ]
HQ_plot = figure(height=450, width=725, title="System Head Requirement",
                 tools="crosshair,pan,reset,save,wheel_zoom",
                 #x_range=[0, 10], y_range=[0, 0.6],
                 tooltips=HQ_TOOLTIPS)

HQ_plot.line('Q', 'im', source=im_source,
             color='black',
             line_dash='dashed',
             line_width=3,
             line_alpha=0.6,
             legend_label='Slurry Graded Cvt=c (m/m)',
             name='Slurry graded Sand Cvt=c')

HQ_plot.line('Q', 'il', source=im_source,
             color='blue',
             line_dash='dashed',
             line_width=2,
             line_alpha=0.3,
             legend_label='Water',
             name='Water')
HQ_plot.extra_x_ranges = {'vel_range': Range1d(pipeline.slurry.vls_list[0], pipeline.slurry.vls_list[-1])}
HQ_plot.add_layout(LinearAxis(x_range_name='vel_range'), 'above')
HQ_plot.xaxis[1].axis_label = f'Velocity (m/sec in {pipeline.slurry.Dp:0.3f}m pipe)'
HQ_plot.xaxis[0].axis_label = f'Flow (m\u00b3/sec)'
HQ_plot.yaxis[0].axis_label = 'Head (m/m)'
HQ_plot.axis.major_tick_in = 10
HQ_plot.axis.minor_tick_in = 7
HQ_plot.axis.minor_tick_out = 0


HQ_plot.legend.location = "top_left"

def update_all(pipeline):
    """Placeholder for an update function"""
    flow_list = [pipeline.pipesections[-1].flow(v) for v in pipeline.slurry.vls_list]
    im_source.data=dict(Q=flow_list,
                        im=[pipeline.calc_system_head(Q)[0] for Q in flow_list],
                        il=[pipeline.calc_system_head(Q)[1] for Q in flow_list],
                        )
    HQ_plot.xaxis[1].axis_label = f'Velocity (m/sec in {pipeline.slurry.Dp:0.3f}m pipe)'
    for i, r in enumerate(pipecol.children):    # iterate over the rows of pipe
        r.children[2].value = f"{pipeline.pipesections[i].diameter:0.3f}"

def pipe_panel(i, pipe):
    """Create a Bokeh row with information about the pipe"""
    return row(TextInput(title="#", value=f'{i:3d}', width=45),
               TextInput(title="Name", value=pipe.name, width=95),
               TextInput(title="Dp (m)", value=f"{pipe.diameter:0.3f}", width=76),
               TextInput(title="Length (m)", value=f"{pipe.length:0.1f}", width=76),
               TextInput(title="Fitting K (-)", value=f"{pipe.total_K:0.2f}", width=76),
               TextInput(title="Delta z (m)", value=f"{pipe.elev_change:0.1f}", width=76),)
pipecol = column([pipe_panel(i, p) for i, p in enumerate(pipeline.pipesections)])

def system_panel(PL):
    """Create a Bokeh Panel with the system elements"""
    return Panel(title="Pipeline", child = row(pipecol, HQ_plot))





