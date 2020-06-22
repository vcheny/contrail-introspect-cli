/*
 * Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
 */

function collapseAll() {
	$("div.accordion-body").each(function(i, element) {
		$(element).collapse('hide');
	});
};

function expandAll() {
	$("div.accordion-body").each(function(i, element) {
		$(element).collapse('show');
	});
};

function wrap() {
	$("pre").css("white-space", "pre-wrap");
};

function noWrap() {
	$("pre").css("white-space", "pre");
};

/* pad string with leading 0's to adjust for the specified width */
function padZero(s, width) {
    var zero = "";
    for (var i = s.length; i < width; ++i) {
        zero += "0";
    }
    return zero + s;
}

/* returns Date() object in string format yyyy-mm-dd hh:mm:ss.sss */
function formatDateTime(dt) {
    // format date
    var yyyy = dt.getFullYear();
    //getMonth() returns 0 - 11. Add 1 to the return value.
    var mm = padZero((dt.getMonth() + 1).toString(), 2);
    var dd = padZero(dt.getDate().toString(), 2);
    var date = yyyy + "-" + mm + "-" + dd;

    // format time
    var hh = padZero(dt.getHours().toString(), 2);
    var mm = padZero(dt.getMinutes().toString(), 2);
    var ss = padZero(dt.getSeconds().toString(), 2);
    var sss = padZero(dt.getMilliseconds().toString(), 3);
    var time = hh + ":" + mm + ":" + ss + "." + sss;

    return date + " " + time;
}

/* converts UTC timestamp in trace message to local timestamp */
function transformTraceMsg() {
    var msgs = document.getElementsByClassName("trace");
    for(var i = 0; i < msgs.length; i++) {
        var msg = msgs[i];
        var utc_ts = msg.innerHTML.split(" ", 1);
        // Date() accepts UTC in milliseconds
        var local_ts = new Date(Number(utc_ts)/1000);
        var ts = formatDateTime(local_ts);
        msg.innerHTML = ts + " " + msg.innerHTML.slice(utc_ts[0].length);
    }
}

/* Encode the special characters in the sandesh request value field */
function sendSandeshRequest(linkx, valuex) {
    var val = encodeURIComponent(valuex);
    window.location.href = 'Snh_'+linkx+'?x='+val;
}

/* Table initialisation */
$(document).ready(function() {
	var $table = $('#struct-or-list-table');
	if($table) {
		$table.dataTable({
			"sDom": "<'row-fluid'<'pull-left'l><'pull-left dt-margin-10'f>r>t<'row-fluid'<'pull-left'p><'pull-left dt-margin-10'i>>",
			"sPaginationType": "bootstrap",
			"oLanguage": {
				"sLengthMenu": "_MENU_ Records per Page"
			}
		});
	}
});
