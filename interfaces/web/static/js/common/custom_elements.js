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

function create_pie_chart(element, data, title, fontColor='white'){
    const labels = [];
    const values = [];
    const backgroundColors = [];
    const hoverBackgroundColors = [];
    let index = 0;
    $.each(data, function (key, value) {
        if(value > 0){
            values.push(value);
            labels.push(key);
            const color = get_color(index);
            backgroundColors.push(color);
            hoverBackgroundColors.push(get_dark_color(index));
            index += 1;
        }
    });
    return new Chart(element.getContext('2d'), {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: backgroundColors,
                    hoverBackgroundColor: hoverBackgroundColors,
                    borderColor: backgroundColors
                }
            ]
        },
        options: {
            responsive: true,
            title: {
                text: title,
                fontColor: fontColor,
                fontSize: 16,
                fontStyle: '',
                display: true
            },
            legend: {
                position: 'bottom',
                labels:{
                    fontColor: fontColor
                }
            }
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
