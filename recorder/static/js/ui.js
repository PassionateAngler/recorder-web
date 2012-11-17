var RecorderUi = RecorderUi || {
    SCRIPT_ROOT : "" ,
    get_timestamp : function(str){
        var d = str.match(/\d+/g); // extract date parts
        if(d){
            return +new Date(d[2], d[1] - 1, d[0], d[3], d[4], 0);
        }else{
            return -1;
        }
    },

    enable_pagination : function(search_uri){
        $('#table-pagination li').not('.active').click(function(){
            $.getJSON(RecorderUi.SCRIPT_ROOT + search_uri, 
                      {p:$(this).text()},
                      RecorderUi.parse_data                 
            );
        });
    },

    parse_data : function(data){
        if(data.error){
            $("#results").text(data.error); 
        }else{
            $("#result_table").remove();
            $("#table-pagination").remove();
            $("#search_results").append(data.recordings_table);
            $("#search_results_header").append(data.pagination);
            $("#records-num").text("Znaleziono: (" +
                data.num + ")");
            $(".tablesorter").tablesorter(); 
            $('.column').equalHeight();
            RecorderUi.enable_pagination('/_ajax_search');
        }
    },
};
