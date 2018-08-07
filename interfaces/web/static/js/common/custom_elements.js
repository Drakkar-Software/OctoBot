function create_circular_progress_doughnut(label1="% Done", label2="% Remaining"){
    return new Chart($("#optimize_doughnutChart")[0].getContext('2d'), {
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