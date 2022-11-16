
var socket = io();

MicroModal.init({
    openTrigger: 'data-custom-open', // [3]
    closeTrigger: 'data-custom-close', // [4]
    disableScroll: true, // [5]
    disableFocus: false, // [6]
    awaitCloseAnimation: false, // [7]
    debugMode: true // [8]
});

$('#dataUsage').tilt({
    maxTilt: 2
})
$('#admin').tilt({
    maxTilt: 2
})

refresh_interval = 60
document.getElementById("data-feed-info").innerText = `Feed refreshes every ${refresh_interval} seconds`

// {"time":time, "temperature":temperature, "pressure":pressure, "humidity":humidity}
bee_datas = []
stats = {}

data_feed = document.getElementById("data-feed")
data_button = document.getElementById("dataButton")
graph_containers = document.getElementsByClassName("graph-container")
admin = document.getElementById("admin")
reset_logs_button = document.getElementById("resetLogsButton")
admin_password = document.getElementById("adminPassword")
clear_memory_button = document.getElementById("clearMemoryButton")

background = document.getElementById("background")
modal_background = document.getElementById("modal-background")
loader = document.getElementById("loader")

async function refresh_data() {
    r = await fetch("/api/data")
    j = await r.json()

    data = j.data

    if (j.error) {
        document.getElementById("error").style.display = "inline-block"
        document.getElementById("error").setAttribute("aria-label", j.message)
    } else {
        document.getElementById("error").style.display = "none"
    }
    
    
    if (data.length > 0 && bee_datas.length == data.length) {
        return
    }
    stats = {}

    // [time, temp, pressure, humidity, resistance]
    bee_datas = []
    for (item of data) {
        bee_datas.push({time:item[0], temperature:item[1], pressure:item[2], humidity:item[3], resistance:item[4]})
    }
    console.log(bee_datas)

    data_feed.innerHTML = ""

    for (data of bee_datas.reverse()) {
        item = `<div class="feed-item">
        <div class="feed-item-title">Recording ${data.time}</div>
        Temperature: ${data.temperature}, Humidity: ${data.humidity}, Pressure: ${data.pressure}, Gas Resistance: ${data.resistance}
        </div>`
        data_feed.innerHTML += item
    }
    await draw_tables()
}

async function resize() {
    for (el of graph_containers) {
        if (isTouchDevice()) {
            el.style.marginTop = "100px"
        }

        if (window.innerWidth > 1500) {
            el.style.width = (window.innerWidth / 2) - 30
        } else {
            el.style.width = `calc(100% - 20px)`
        }
    }   
    
}

document.onscroll = async function() {
    background.style.backgroundPosition = `0 ${0-window.scrollY /5}px`
}
document.onmousemove = async function(e) {
    
    modal_background.style.backgroundPosition = `${0-e.clientX/30} ${0-e.clientY/30}`
}

password = null

admin.onclick = async function(e) {
    if (!e.target.classList.contains("admin")) return

    adminContent = document.getElementById("adminContent")
    if (adminContent.style.height == "0px" || adminContent.style.height == 0) {
        // Currently closed 
        if (!password) {
            
            MicroModal.show('modal-2', {
                onClose: async function(modal) {
                    MicroModal.show("modal-1")
                }
            });
        } else {
            adminContent.style.height = "300px"
            document.getElementById("adminChevron").style.transform = "rotate(180deg)"
        }
    } else {
        adminContent.style.height = "0"
        document.getElementById("adminChevron").style.transform = "rotate(0deg)"
    }
}
admin_password.oninput = async function() {
    
    r = await fetch(`/api/password?pwd=${encodeURIComponent(admin_password.value)}`)
    j = await r.json()
    if (j.valid) {
        password = admin_password.value
        MicroModal.close('modal-2');
        MicroModal.show('modal-1');
        adminContent.style.height = "300px"
        document.getElementById("adminChevron").style.transform = "rotate(180deg)"
    }
}

reset_logs_button.onclick = async function() {
    loader.style.display = "inline-block"
    r = await fetch(`/api/stats?pwd=${encodeURIComponent(admin_password.value)}`, {method: 'DELETE'})
    data = await r.json()

    if (data.error) {
        nt = await notifications.new("Error", data.message)
        nt.style.backgroundColor = "rgb(255, 0, 0, 0.2)"
    } else {
        stats = data.data
    }

    loader.style.display = "none"
    updateStats()
}
clear_memory_button.onclick = async function() {
    loader.style.display = "inline-block"
    r = await fetch(`/api/data?pwd=${encodeURIComponent(admin_password.value)}`, {method: 'DELETE'})
    data = await r.json()

    if (data.error) {
        nt = await notifications.new("Error", data.message)
        nt.style.backgroundColor = "rgb(255, 0, 0, 0.2)"
    } else {
        stats = data.data
    }

    loader.style.display = "none"
    await refresh_data()
}

async function updateStats() {
    document.getElementById("total-data").innerText = formatFileSize(stats[2], 2)
    document.getElementById("total-requests").innerText = stats[1]

    last_reset = new Date(stats[0]);
    document.getElementById("last-reset").innerText = `${ordinal_suffix_of(last_reset.getDate())} ${monthNames[last_reset.getMonth()]} ${last_reset.getFullYear()} at ${last_reset.getHours()}:${last_reset.getMinutes()}`

}

data_button.onclick = async function() {
    if (Object.keys(stats).length === 0) {
        loader.style.display = "inline-block"
        r = await fetch("/api/stats")
        data = await r.json()

        if (data.error) {
            nt = await notifications.new("Error", data.message)
            nt.style.backgroundColor = "rgb(255, 0, 0, 0.5)"

            document.getElementById("error").style.display = "inline-block"
            document.getElementById("error").setAttribute("aria-label", data.message)

        } else {
            stats = data.data
            updateStats()
            document.getElementById("error").style.display = "none"
            MicroModal.show('modal-1');
        }

        loader.style.display = "none"
    } else {
        updateStats()
        MicroModal.show('modal-1');
    }

    
}

if (isTouchDevice()) {
    document.getElementById("tip").innerText = "Pinch on a graph to zoom."
}

socket.on("connect", function() {
    console.log("connected")
})
socket.on('data', async function(msg) {
    if (msg == "new") {
        await refresh_data()
    }
})

window.onresize = resize 
resize()

window.onload = refresh_data 

setInterval(refresh_data, refresh_interval * 1000)


