/*
 * Drakkar-Software OctoBot
 * Copyright (c) Drakkar-Software, All rights reserved.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3.0 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.
 */

function create_circular_progress_doughnut(element, label1="% Done", label2="% Remaining"){
    return new Chart(element.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: [label1, label2],
            datasets: [
                {
                    data: [0, 100],
                    backgroundColor: ["#F7464A","#949FB1"],
                    hoverBackgroundColor: ["#FF5A5E", "#A8B3C5"]
                }
            ]
        },
        options: {
            responsive: true,
            cutoutPercentage: 80
        }
    });
}

function create_doughnut_chart(element, data, title, displayLegend=true, graphHeight=400, update){
    const labels = [];
    const values = [];
    const backgroundColors = [];
    let index = 0;
    let totalValue = 0;
    $.each(data, function (_, value) {
        totalValue += value;
    });
    $.each(data, function (key, value) {
        if(value > 0){
            values.push(value);
            labels.push(`${key} ${(value/totalValue*100).toFixed(2)}%`);
            const color = get_color(index);
            backgroundColors.push(color);
            index += 1;
        }
    });
    const plottedData = [{
        values: values,
        labels: labels,
        marker: {
            colors: backgroundColors
        },
        textinfo: 'none',
        type: "pie"
    }]
    const layout = {
        height: graphHeight,
        legend: {
            orientation: isMobileDisplay() ? "h": "v",
            font: {
                color: getTextColor()
            }
        },
        showlegend: displayLegend,
        margin: {
            t: 0,
            b: 0,
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
    }
    const plotlyConfig = {
        scrollZoom: false,
        responsive: true,
        displayModeBar: false
    };
    if (update){
        // Plotly.restyle(element, plottedData); // todo use restyle for better perf
        Plotly.newPlot(element, plottedData, layout, plotlyConfig);
    } else {
        Plotly.newPlot(element, plottedData, layout, plotlyConfig);
    }
}

function create_line_chart(element, data, title, fontColor='white', update=true, height=undefined){
    const trace = {
      x: data.map((e) => new Date(e.time*1000)),
      y: data.map((e) => e.value),
      fill: "tonexty",
      type: 'scatter',
      line: {shape: 'spline'},
    };
    const minY = Math.min.apply(null, trace.y);
    const maxDisplayY = Math.max.apply(null, trace.y);
    const minDisplayY = Math.max(0, minY - ((maxDisplayY - minY) / 2));
    const titleSpecs = {
        text: title,
        font: {
            size: 24
        },
    };
    const layout = {
        title: titleSpecs,
        height: height,
        dragmode: isMobileDisplay() ? false : 'zoom',
        margin: {
            l: 30,
            r: 0,
            t: 40,
            b: 40,
        },
        xaxis: {
            autorange: true,
            showgrid: false,
            domain: [0, 1],
            type: 'date',
            rangeslider: {
                visible: false,
            },
            automargin: true,
        },
        yaxis1: {
            showgrid: false,
            range: [minDisplayY, maxDisplayY],
            automargin: true,
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            color: fontColor
        },
    };
    const plotlyConfig = {
        staticPlot: isMobileDisplay(),
        scrollZoom: false,
        modeBarButtonsToRemove: ["select2d", "lasso2d", "toggleSpikelines"],
        responsive: true,
        showEditInChartStudio: false,
        displaylogo: false // no logo to avoid 'rel="noopener noreferrer"' security issue (see https://webhint.io/docs/user-guide/hints/hint-disown-opener/)
    };
    if(update){
        const layoutUpdate = {
            title: titleSpecs
        }
        Plotly.update(element, {x: [trace.x], y: [trace.y]}, layoutUpdate, 0);
    } else {
        Plotly.newPlot(element, [trace], layout, plotlyConfig);
    }
}

function create_histogram_chart(element, data, titleY1, titleY2, nameYAxis, fontColor='gray', update=true){
    const trace1 = {
      x: data.map((e) => new Date(e.time*1000)),
      y: data.map((e) => e.y1),
      marker: {
         color: getTextColor(),
      },
      opacity: 0.9,
      line: {
        width: 4,
      },
      type: 'scatter',
      name: titleY1,
    };
    // rgb(198,40,40) octobot red
    // rgb(0,142,0) green
    const trace2 = {
      x: data.map((e) => new Date(e.time*1000)),
      y: data.map((e) => e.y2),
      marker: {
         color: data.map((e) => e.y2 > 0 ? 'rgba(0,142,0,.8)': 'rgba(198,40,40,.5)'),
          line: {
            color: data.map((e) => e.y2 > 0 ? 'rgb(0,142,0)': 'rgb(198,40,40)'),
            width: 1.5,
          }
      },
      yaxis: 'y2',
      type: 'bar',
      name: titleY2,
    };
    const maxDisplayY = Math.max(0, Math.max.apply(null, trace2.y) * 1.5);
    const minDisplayY = Math.min(0, Math.min.apply(null, trace2.y) * 1.5);
    const layout = {
        dragmode: isMobileDisplay() ? false : 'zoom',
        xaxis: {
            autorange: true,
            showgrid: false,
            domain: [0, 1],
            type: 'date',
            rangeslider: {
                visible: false,
            }
        },
        yaxis1: {
            showgrid: true,
            overlaying: 'y2',
            title: nameYAxis,
            rangemode: "tozero",
            gridcolor: "grey"
        },
        yaxis2: {
            rangemode: "tozero",
            showgrid: false,
            showticklabels: false,
            side: 'right',
            range: [minDisplayY, maxDisplayY],
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            color: fontColor
        },
        margin: {
            l: 30,
            r: 30,
            t: 40,
        },
        showlegend: false,
    };
    const plotlyConfig = {
        staticPlot: isMobileDisplay(),
        scrollZoom: false,
        modeBarButtonsToRemove: ["select2d", "lasso2d", "toggleSpikelines"],
        responsive: true,
        showEditInChartStudio: false,
        displaylogo: false // no logo to avoid 'rel="noopener noreferrer"' security issue (see https://webhint.io/docs/user-guide/hints/hint-disown-opener/)
    };
    if(update){
        Plotly.restyle(element, {x: [trace1.x], y: [trace1.y], y2: [trace2.y]}, 0);
    } else {
        Plotly.newPlot(element, [trace1, trace2], layout, plotlyConfig);
    }
}

function update_circular_progress_doughnut(chart, done, remaining){
    chart.data.datasets[0].data[0] = done;
    chart.data.datasets[0].data[1] = remaining;
    chart.update();
}

function create_bars_chart(element, labels, datasets, min_y=0, displayLegend=true, fontColor='white', zeroLineColor='black'){
    return new Chart(element.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            legend: {
                display: displayLegend,
                labels: {
                    fontColor: fontColor,
                    fontSize: 15
                }
            },
            scales:{
                xAxes:[{
                    ticks:{
                          fontColor: fontColor,
                          fontSize: 14
                    }
                }],
                yAxes:[{
                    ticks:{
                        fontColor: fontColor,
                        fontSize: 14,
                        suggestedMin: min_y
                    },
                    gridLines:{
                        zeroLineColor: zeroLineColor
                    }
                }]
            }
        }
    });
}

function update_bars_chart(chart, datasets){
    chart.data.datasets[0].data = datasets[0].data;
    chart.data.datasets[0].backgroundColor = datasets[0].backgroundColor;
    chart.data.datasets[0].borderColor = datasets[0].borderColor;
    chart.update();
}
