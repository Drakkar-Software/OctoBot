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