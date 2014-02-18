$(function () {
    var pager = $("div#pager");
    var ul = $('<ul class="pagination" />');
    $("div#pager *").each(function (k, v) {
	console.log(k, v);
        var li = $("<li/>");
        li.html($(this));
        ul.append(li);
    }).promise()
        .done(function () {
            pager.html(ul);
            pager.show();
        });
});

