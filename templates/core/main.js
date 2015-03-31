 $(document).ready(function() {
   $('#itemHistoryPanel').hide();
   $('#itemHistoryButton').click(function() {
        $('#itemHistoryPanel').toggle("normal");
   });
   $('.statusitem').hover(
			 function() { $('ul', this).css('display', 'block'); },
			 function() { $('ul', this).css('display', 'none'); }
    );
     $('.statusactions > li').hover(
			function() { $(this).css('background-color', '#FFFFCC'); },
			function() { $(this).css('background-color', ''); }
    );
   $('li.log,li.makecomplete,li.resethere').click(function(e){
        var item = $('a', this).attr('item');
        var action = $('a', this).attr('action');
        var status = $('a', this).attr('status');
        $.ajax({
            type: "POST",
            url: "/django/workflow/status/change/" + action + "/" + status + "/",
            data: "item=" + item + "&user={{ user.id }}",
            dataType: "html",
            success: function(msg){
                 if (status == "True") { $('#' + item + '_' + action).attr('class', 'complete'); }
                 if (status == "False") { $('#' + item + '_' + action).attr('class', 'incomplete'); }
                window.location.reload();
            },
            error: function(msg) {
                alert( "Problem saving data: " + msg);
            }   
        });

    });

    $('input.batch_active_status').click(function() {
        var batch = $(this).attr('batch');
        $.ajax({
            type: "GET",
            url: "/django/workflow/batch/" + batch + "/change_active/",
            dataType: "html",
            success: function(msg){
                window.location.reload();
            },
            error: function(msg) {
                alert( "Problem saving data: " + msg);
            }   
        });
    });

    $('td.ready,li.ready').click(function(e){
        var item = $(this).attr('item');
        var action = $(this).attr('action');

        $("#action_dialog").dialog({
    		bgiframe: true,
    		resizable: false,
    		modal: true,
    		overlay: {
    			backgroundColor: '#000',
    			opacity: 0.3
    		},
    		buttons: {
    			'complete task': function() {
    				$("#action_dialog").dialog('close');
                                var status = "True";
                                $.ajax({
                                    type: "POST",
                                    url: "/django/workflow/status/change/" + action + "/" + status + "/",
                                    data: "item=" + item + "&user={{ user.id }}",
                                    dataType: "html",
                                    success: function(msg){
                                         if (status == "True") { $('#' + item + '_' + action).attr('class', 'complete'); }
                                         if (status == "False") { $('#' + item + '_' + action).attr('class', 'incomplete'); }
                                        window.location.reload();
                                    },
                                    error: function(msg) {
                                        alert( "Problem saving data: " + msg);
                                    }   
                                });
    			},
    			'log progress': function() {
    				$("#action_dialog").dialog('close');
                                var status = "log";
                                $.ajax({
                                    type: "POST",
                                    url: "/django/workflow/status/change/" + action + "/" + status + "/",
                                    data: "item=" + item + "&user={{ user.id }}",
                                    dataType: "html",
                                    success: function(msg){
                                         if (status == "True") { $('#' + item + '_' + action).attr('class', 'complete'); }
                                         if (status == "False") { $('#' + item + '_' + action).attr('class', 'incomplete'); }
                                        window.location.reload();
                                    },
                                    error: function(msg) {
                                        alert( "Problem saving data: " + msg);
                                    }   
                                });
    			},
    			cancel: function() {
    				$("#action_dialog").dialog('close');
    			}
    		}
        });
	$("#action_dialog").dialog('open');
	})
	.hover(
			function(){ 
				$(this).addClass("makecomplete"); 
			},
			function(){ 
				$(this).removeClass("makecomplete"); 
			});

     $('li.complete').click(function(e){
        var item = $(this).attr('item');
        var action = $(this).attr('action');
        $("#reset_dialog").dialog({
    		bgiframe: true,
    		resizable: false,
    		modal: true,
    		overlay: {
    			backgroundColor: '#000',
    			opacity: 0.3
    		},
    		buttons: {
    			'reset to here': function() {
    				$("#reset_dialog").dialog('close');
                                var status = "False";
                                $.ajax({
                                    type: "POST",
                                    url: "/django/workflow/status/change/" + action + "/" + status + "/",
                                    data: "item=" + item + "&user={{ user.id }}",
                                    dataType: "html",
                                    success: function(msg){
                                         if (status == "True") { $('#' + item + '_' + action).attr('class', 'complete'); }
                                         if (status == "False") { $('#' + item + '_' + action).attr('class', 'incomplete'); }
                                        window.location.reload();
                                    },
                                    error: function(msg) {
                                        alert( "Problem saving data: " + msg);
                                    }   
                                });
    			},
    			cancel: function() {
    				$("#reset_dialog").dialog('close');
    			}
    		}
        });
	$("#reset_dialog").dialog('open');
	})
	.hover(
			function(){ 
				$(this).addClass("makecomplete"); 
			},
			function(){ 
				$(this).removeClass("makecomplete"); 
			});

	$(".striped tr:odd").addClass("odd");

 });
