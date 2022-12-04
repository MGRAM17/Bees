
function formatDate(d) {
    var date_format_str = d.getFullYear().toString()+"-"+((d.getMonth()+1).toString().length==2?(d.getMonth()+1).toString():"0"+(d.getMonth()+1).toString())+"-"+(d.getDate().toString().length==2?d.getDate().toString():"0"+d.getDate().toString())+" "+(d.getHours().toString().length==2?d.getHours().toString():"0"+d.getHours().toString())+":"+((parseInt(d.getMinutes()/5)*5).toString().length==2?(parseInt(d.getMinutes()/5)*5).toString():"0"+(parseInt(d.getMinutes()/5)*5).toString())+":00";
    return date_format_str

}

notifications = {
    notifications:[],
    close : async function (notification) {
        document.body.style.overflowX = "hidden"
        notification.style.right = "-550px"
            
        setTimeout(function() {
            notification.remove()
            document.body.style.overflowX = "auto"
        }, 500)
    },
    new : async function (title, message, onclick = null) {
        for (notification of this.notifications) {
            await notifications.close(notification)
        }

        document.body.style.overflowX = "hidden"

        notification = document.createElement("div")
        notification.classList = "notification noselect"

        notificationTitle = document.createElement("div")
        notificationTitle.classList = "title"
        notificationTitle.style.fontFamily = "Poppins"
        notificationTitle.style.fontWeight = "700"
        notificationTitle.style.fontSize = "30px"
        notificationTitle.innerText = title 

        notificationMessage = document.createElement("div")
        notificationMessage.innerText = message 

        notificationClose = document.createElement("i")
        notificationClose.classList = "fa fa-times notification-close"
        notificationClose.onclick = async function() {
            await notifications.close(notification)
        }

        
        notification.appendChild(notificationTitle)
        notification.appendChild(notificationMessage)
        notification.appendChild(notificationClose)
        
        if (onclick) {
            notification.onmouseover = function() {notification.style.textDecoration = "underline"}
            notification.onmouseout = function() {notification.style.textDecoration = "none"}
            notification.onclick = onclick
            notification.style.cursor = "pointer"
        } else {
            notification.onclick = notificationClose.onclick
        }
        

        document.body.appendChild(notification)

        notifications.notifications.push(notification)

        notification.style.right = "15px"

        setTimeout(notificationClose.onclick, (message.length + title.length) * 150)

        return notification
    }
}

function isTouchDevice() {
    return (('ontouchstart' in window) ||
        (navigator.maxTouchPoints > 0) ||
        (navigator.msMaxTouchPoints > 0));
}

function formatFileSize(bytes,decimalPoint) {
    if(bytes == 0) return '0 Bytes';
    var k = 1000,
        dm = decimalPoint || 2,
        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
        i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
 }

 function ordinal_suffix_of(i) {
    var j = i % 10,
        k = i % 100;
    if (j == 1 && k != 11) {
        return i + "st";
    }
    if (j == 2 && k != 12) {
        return i + "nd";
    }
    if (j == 3 && k != 13) {
        return i + "rd";
    }
    return i + "th";
}

const monthNames = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];