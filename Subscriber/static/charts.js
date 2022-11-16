
var myChart = null

charts = {}

async function generate_time_chart(data, element) {  
    if (charts[element.id]) {
        charts[element.id].config.data = {datasets:data}
        charts[element.id].update()
        return;
    }

    charts[element.id] = new Chart(element.getContext('2d'), {
        type: 'line',
        data: {
            datasets: data,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            tension:0.2,
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            scales: {
                xAxis: {
                    type: 'time',
                }
            },
            animation: {
                onComplete: function() {
                    loader.style.display = "none"
                }
            },
            plugins: {
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'x',
                        scaleMode: 'y'
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                            modifierKey: "shift"
                        },
                        pinch: {
                            enabled: true,
                        },
                        mode: 'x',
                        scaleMode: 'y'
                    }
                }
            }
        }
        
    });

    
}



async function draw_tables() {
    loader.style.display = "inline-block"


    if (bee_datas.length > 10) {
        trendline = {
            colorMin: "red",
            colorMax: "green",
            lineStyle: "dotted",
            width: 2,
            projection: false
        }
    } else {
        trendline = null
    }


    temp_data = []
    humidity_data = []
    pressure_data = []
    resistance_data = []

    for (bee_data of bee_datas.reverse()) {
        temp_data.push({x:new Date(bee_data.time), y:bee_data.temperature})
        humidity_data.push({x:new Date(bee_data.time), y:bee_data.humidity})
        pressure_data.push({x:new Date(bee_data.time), y:bee_data.pressure})
        resistance_data.push({x:new Date(bee_data.time), y:bee_data.resistance})
    }

    await generate_time_chart([
            {
                label:"Temperature",
                data: temp_data,
                borderColor:"blue",
                trendlineLinear: trendline
            }
        ],
        document.getElementById('temperatureChart')
    )

    await generate_time_chart([
            {
                label:"Humidity",
                data: humidity_data,
                borderColor:"red",
                trendlineLinear: trendline
            }
        ],
        document.getElementById('humidityChart')
    )

    await generate_time_chart([
            {
                label:"Pressure",
                data: pressure_data,
                borderColor:"green"
            }
        ],
        document.getElementById('pressureChart')
    )

    await generate_time_chart([
            {
                label:"Gas Resistance",
                data: resistance_data,
                borderColor:"purple"
            }
        ],
        document.getElementById('resistanceChart')
    )

}

document.getElementById("resetButton").onclick = async function() {
    for (chart in charts) {
        charts[chart].resetZoom();
    }
}
