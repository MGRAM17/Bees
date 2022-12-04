
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
$('#filters').tilt({
    maxTilt: 2
})

refresh_interval = 60
document.getElementById("data-feed-info").innerText = `Feed refreshes every ${refresh_interval} seconds`

// {"time":time, "temperature":temperature, "pressure":pressure, "humidity":humidity}
bee_datas = []
stats = {}
prev_data = []

data_feed = document.getElementById("data-feed")
data_button = document.getElementById("dataButton")
graph_containers = document.getElementsByClassName("graph-container")
admin = document.getElementById("admin")
reset_logs_button = document.getElementById("resetLogsButton")
admin_password = document.getElementById("adminPassword")
clear_memory_button = document.getElementById("clearMemoryButton")
enable_desktop_button = document.getElementById("enableDesktopButton")
disable_desktop_button = document.getElementById("disableDesktopButton")
reboot_button = document.getElementById("rebootButton")

background = document.getElementById("background")
modal_background = document.getElementById("modal-background")
loader = document.getElementById("loader")
filter_start = document.getElementById("filter-start")
filter_finish = document.getElementById("filter-finish")
filters_reset = document.getElementById("filters-reset")
filter_resolution = document.getElementById("filter-resolution")

var start
var finish
var resolution

default_resolution = 1

async function refresh_data(inp_data) {
    
    if (!inp_data) {
        
        if (resolution) {
            every = resolution
        } else {
            every = "auto"
        }

        params = `every=${every}`
        if (start) {
            params += `&start=${formatDate(start)}`
        } if (finish) {
            params += `&finish=${formatDate(finish)}`
        }

        r = await fetch(`/api/data?${params}`)
        j = await r.json()

        data = j.data
        default_resolution = j.every
        prev_data = data

        if (j.error) {
            document.getElementById("error").style.display = "inline-block"
            document.getElementById("error").setAttribute("aria-label", j.message)
        } else {
            document.getElementById("error").style.display = "none"
        }
    } else {
        data = inp_data
        document.getElementById("error").style.display = "none"
    }

    
    if (data.length > 0 && !inp_data && bee_datas.length == data.length) {
        return
    }
    
    stats = {}

    // [time, temp, pressure, humidity, resistance]
    bee_datas = []
    for (item of data) {
        bee_datas.push({time:item[0], temperature:item[1], pressure:item[2], humidity:item[3], resistance:item[4]})
    }
    if (bee_datas.length > 0 && !start) {
        var d = new Date(bee_datas[0].time);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
        filter_start.value = d.toISOString().slice(0,16);
    }
    if (!resolution) {
        filter_resolution.value = default_resolution
    }
    

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

filters_reset.onclick = async function() {
    
    start = null 
    finish = null
    resolution = null
    
    var d = new Date(prev_data[0][0]);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
    filter_start.value = ""
    filter_finish.value = ""
    

    await refresh_data()
}

resolution_counter = null

filter_start.onchange = async function(e) {
    start = new Date(e.target.value)
    await refresh_data()
}
filter_finish.onchange = async function(e) {
    finish = new Date(e.target.value)
    await refresh_data()
}
filter_resolution.oninput = async function(e) {
    clearTimeout(resolution_counter)

    resolution_counter = setTimeout(async function() {
        resolution = filter_resolution.value 
        await refresh_data()
    }, 1000)
    
    
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
enable_desktop_button.onclick = async function() {
    loader.style.display = "inline-block"
    r = await fetch(`/api/enable_desktop?pwd=${encodeURIComponent(admin_password.value)}`, {method: 'GET'})
    data = await r.json()

    if (data.error) {
        nt = await notifications.new("Error", data.message)
        nt.style.backgroundColor = "rgb(255, 0, 0, 0.2)"
    } else {
        nt = await notifications.new("Successfully enabled", data.message)
        nt.style.backgroundColor = "rgb(0, 255, 0, 0.2)"
        stats[3] = "desktop"
        updateStats()
    }
    loader.style.display = "none"
    
}
disable_desktop_button.onclick = async function() {
    loader.style.display = "inline-block"
    r = await fetch(`/api/disable_desktop?pwd=${encodeURIComponent(admin_password.value)}`, {method: 'GET'})
    data = await r.json()

    if (data.error) {
        nt = await notifications.new("Error", data.message)
        nt.style.backgroundColor = "rgb(255, 0, 0, 0.2)"
    }  else {
        nt = await notifications.new("Successfully disabled", data.message)
        nt.style.backgroundColor = "rgb(0, 255, 0, 0.2)"
        stats[3] = "terminal"
        updateStats()
    }

    loader.style.display = "none"
}
reboot_button.onclick = async function() {
    loader.style.display = "inline-block"
    r = await fetch(`/api/reboot?pwd=${encodeURIComponent(admin_password.value)}`, {method: 'GET'})
    data = await r.json()

    if (data.error) {
        nt = await notifications.new("Error", data.message)
        nt.style.backgroundColor = "rgb(255, 0, 0, 0.2)"
    } else {
        nt = await notifications.new("Successfully rebooted", data.message)
        nt.style.backgroundColor = "rgb(0, 255, 0, 0.2)"
    }

    loader.style.display = "none"
}

async function updateStats() {
    document.getElementById("total-data").innerText = formatFileSize(stats[2], 2)
    document.getElementById("total-requests").innerText = stats[1]

    last_reset = new Date(stats[0]);
    document.getElementById("last-reset").innerText = `${ordinal_suffix_of(last_reset.getDate())} ${monthNames[last_reset.getMonth()]} ${last_reset.getFullYear()} at ${last_reset.getHours()}:${last_reset.getMinutes()}`
    document.getElementById("gui").innerText = `The computer is currently in ${stats[3]} mode.`
    if (stats[3] == "desktop") {
        enable_desktop_button.style.filter = "brightness(80%)"
        disable_desktop_button.style.filter = "brightness(100%)"
    } else {
        enable_desktop_button.style.filter = "brightness(100%)"
        disable_desktop_button.style.filter = "brightness(80%)"
    }
}

data_button.onclick = async function() {
    MicroModal.show('modal-1');

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
        }

        loader.style.display = "none"
    } else {
        updateStats()
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
socket.on('errors', async function(msg) {
    document.getElementById("error").style.display = "inline-block"
    document.getElementById("error").setAttribute("aria-label", msg)
})

window.onresize = resize 
resize()

window.onload = async function() {
    await refresh_data()
} 

setInterval(async function() {
    await refresh_data()
} , refresh_interval * 1000)


