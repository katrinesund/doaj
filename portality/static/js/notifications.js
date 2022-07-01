doaj.notifications = {};
doaj.notifications.top_url = "/dashboard/top_notifications";
doaj.notifications.seen_url = "/dashboard/notifications/{notification_id}/seen"
doaj.notifications.page_url = "/dashboard/notifications"

doaj.notifications.init = function() {
    $.ajax({
        method: "get",
        url: doaj.notifications.top_url,
        contentType: "application/json",
        dataType: "jsonp",
        success: doaj.notifications.notificationsReceived
    })
}

doaj.notifications.notificationsReceived = function(data) {
    let frag = "";
    let unseenCount = 0;
    for (let i = 0; i < data.length; i++) {
        let notification = data[i];
        let seenClass = notification.seen_date ? "notification__seen" : "notifications__unseen";
        if (!notification.seen_date) {
            unseenCount++;
        }
        frag += `<li class="notifications__item">
            <a href="${notification.action}" class="dropdown__link ${seenClass} notification_action_link" data-notification-id="${notification.id}">
                <span>${notification.short ? notification.short : "Untitled notification"}</span>
                <small class="notifications__date"><time datetime="${notification.created_date}">${doaj.humanDate(notification.created_date)}</time></small>
            </a>
        </li>`;
    }
    frag += `<li>
      <a href="${doaj.notifications.page_url}" class="dropdown__link">
          See all notifications
      </a>
    </li>`;

    $("#top_notifications").html(frag);

    if (unseenCount > 0) {
        $(".js-notifications-count").html(`(${unseenCount})`);
    } else {
        $(".js-notifications-count").html("");
    }

    $(".notification_action_link").on("click", doaj.notifications.notificationClicked);
}

doaj.notifications.notificationClicked = function(event) {
    let el = $(this);
    let notificationId = el.attr("data-notification-id");
    doaj.notifications.setAsSeen(notificationId, el);
}

doaj.notifications.setAsSeen = function(notificationId, element) {
    $.ajax({
        method: "post",
        url: doaj.notifications.seen_url.replace("{notification_id}", notificationId),
        contentType: "application/json",
        dataType: "jsonp"
    });
    element.removeClass("notifications__unseen").addClass("notification__seen");
}

jQuery(document).ready(function($) {
    doaj.notifications.init();
});
