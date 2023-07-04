if (!doaj.hasOwnProperty("tourist")) { doaj.tourist = {}}

doaj.tourist.currentTour = null;
doaj.tourist.contentId = null;

doaj.tourist.init = function(params) {
    let tours = params.tours || [];
    let cookiePrefix = params.cookie_prefix;
    let cookies = document.cookie.split("; ");

    let first = false;
    for (let tour of tours) {
        let cookieName = cookiePrefix + tour.content_id + "=" + tour.content_id;
        let cookie = cookies.find(c => c === cookieName);
        if (!cookie) {
            first = tour;
            break;
        }
    }

    if (first) {
        doaj.tourist.start(first);
    }
}

doaj.tourist.start = function (tour) {
    doaj.tourist.contentId = tour.content_id;
    doaj.tourist.currentTour = new Tourguide({
        src: `/tours/${tour.content_id}`,
        onStart: doaj.tourist.startCallback
    });
    doaj.tourist.currentTour.start()
}

doaj.tourist.startCallback = function(options) {
    doaj.tourist.seen({tour: doaj.tourist.contentId});
}

doaj.tourist.seen = function(params) {
    $.ajax({
        type: "GET",
        url: `/tours/${doaj.tourist.contentId}/seen`,
        success: function() {}
    })
}