function init_statistics_panel(botid, target, url) {
    var targetid = target.replace('#', '_');

    $('#' + targetid + '-chart-action-1').click(function () {
        get_statistics_data(botid, target, url, 2, 7);
        $('#' + targetid + '-chart-title').text('7天').attr('last-status', targetid + '-chart-action-1');
    });

    $('#' + targetid + '-chart-action-2').click(function () {
        get_statistics_data(botid, target, url, 2, 30);
        $('#' + targetid + '-chart-title').text('30天').attr('last-status', targetid + '-chart-action-2');
    });

    $('#' + targetid + '-chart-action-3').click(function () {
        get_statistics_data(botid, target, url, 2, 60);
        $('#' + targetid + '-chart-title').text('60天').attr('last-status', targetid + '-chart-action-3');
    });

    $('#' + targetid + '-chart-action-4').click(function () {
        var $title = $('#' + targetid + '-chart-title');
        var title = $title.text();
        $title.text('重算中...');
        get_statistics_data(botid, target, url, 3, 1);
        $title.text(title);
        $('#' + $title.attr('last-status')).trigger("click");
    });

    $('#' + targetid + '-rank-action-1').click(function () {
        get_statistics_data(botid, target, url, 4, 0);
        $('#' + targetid + '-rank-title').text('今天');
    });

    $('#' + targetid + '-rank-action-2').click(function () {
        get_statistics_data(botid, target, url, 4, 1);
        $('#' + targetid + '-rank-title').text('昨天');
    });


    $('#' + targetid + '-rank-action-3').click(function () {
        get_statistics_data(botid, target, url, 4, 7);
        $('#' + targetid + '-rank-title').text('7天内');
    });


    $('#' + targetid + '-rank-action-4').click(function () {
        get_statistics_data(botid, target, url, 4, 99999);
        $('#' + targetid + '-rank-title').text('全部');
    });

    $(document).ready(function () {
        get_statistics_data(botid, target, url, 1, 0);
        setInterval(function () {
            get_statistics_data(botid, target, url, 1, 0);
            get_statistics_data(botid, target, url, 3, 1);
            $('#' + $title.attr('last-status')).trigger("click");
        }, 30000);
        $('#' + targetid + '-chart-action-3').trigger("click");
        $('#' + targetid + '-rank-action-1').trigger("click");
    });
}

function get_statistics_data(botid, target, url, type, days) {
    var targetid = target.replace('#', '_');
    $.ajax({
        url: url,
        type: 'POST',
        dataType: 'json',
        data: {"type": type, "botid": botid, "target": target, "days": days},
        success: function (data) {
            if (data.success === 1) {
                if (type === 1) {
                    // 汇总数据
                    $('#speak_today_count').text(data.data.statistics_data.speak_today_count);
                    $('#sign_today_count').text(data.data.statistics_data.sign_today_count);
                    $('#point_today_total').text(data.data.statistics_data.point_today_total);
                    $('#score_today_total').text(data.data.statistics_data.score_today_total);
                } else if (type === 2) {
                    // 查询发言统计
                    if (data.data.statistics_data.length > 0) {
                        $('#' + targetid + '-chart').html('');
                        Morris.Line({
                            element: targetid + '-chart',
                            data: data.data.statistics_data,
                            xkey: 'date',
                            ykeys: ['message_count', 'vaild_count'],
                            labels: ['消息总数', '有效消息总数'],
                            lineColors: ['#4f81bd', '#f79646'],
                            ymax: data.data.max_speaks,
                            ymin: data.data.min_speaks,
                            pointSize: 2,
                            continuousLine: false,
                            hideHover: false,
                            resize: true
                        });
                    } else {
                        $('#' + targetid + '-chart').html('<div class="text-center text-info">暂无数据!</div>')
                    }
                } else if (type === 3) {
                    // 重新计算发言统计

                } else if (type === 4) {
                    // 发言排行榜
                    var $tops = data.data.statistics_data;
                    var $rank = $("#" + targetid + "-rank");

                    $rank.empty();
                    if ($tops.length > 0) {
                        for (var i = 0; i < $tops.length; i++) {
                            var htmlstr = [];
                            htmlstr.push('<li>');
                            htmlstr.push('    <div class="list-group-item">');
                            htmlstr.push('        <div class="top-number">' + (i + 1) + '</div>');
                            htmlstr.push('        <div class="top-id">' + $tops[i].id + '</div>');
                            htmlstr.push('        <div class="top-name">' + $tops[i].name + '</div>');
                            htmlstr.push('        <span class="pull-right text-muted small"><em>' + $tops[i].count + '</em></span>');
                            htmlstr.push('    </div>');
                            htmlstr.push('</li>');
                            $rank.append(htmlstr.join("\n"));
                        }
                    } else {
                        $rank.append('<div class="panel-body text-center text-info">暂无数据!</div>');
                    }
                }
            } else {

            }
        }
    });
}