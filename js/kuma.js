//
// kuma.js
//
// $Id$
//
// Copyright(C) zolo, All rights reserved.
//

function filter_change (e){

    // name : filter, value : all, fakelist, intime, capital, artifact
    // name : player, value : uid

    var name    = e.name;
    var value   = e.value;
    var checked = e.checked;

    var mergin  = document.getElementById("mergin");
    var xx      = document.getElementById("xx");
    var yy      = document.getElementById("yy");
    var vel     = document.getElementById("vel");
    var tsq     = document.getElementById("tsq");
    var id      = document.getElementById("id");
    var arrival = document.getElementById("arrival");

    var para = "x=" + xx.value + "&y=" + yy.value + "&vel=" + vel.value + "&tsq=" + tsq.value;
    para += "&id=" + id.value + "&mergin=" + mergin.value ;
    para += "&arrival=" + encodeURI(arrival.value);

    var values ;
    
    if ( name == "filter" && value == "all" ){
	values = ["fakelist", "intime", "capital", "artifact"];
    } else {
	values = [value];
    }
    var vlen = values.length;

    var ix;
    for(ix=0;ix<clen;ix++){
	var val = values[ix];
	
	var idname = "vt_" + name + "_" + val;
	var vt = document.getElementById(idname);

	if( !checked && vt.innerHTML == "" ){
	    continue;
	} else if ( !checked ){
	    vt.style.display = "none";
	    continue;
	} else if ( checked && vt.innerHTML != "" ){
	    vt.style.display = "block";  # display
	    // continue;
	}
	vt.style.display = "block";  # display
	// checked and vt.innerHTML == ""
	var xhr = new XMLHttpRequest();
	var url = "http://" + "$httphost" + "/$script/filter/" + name + "/" + val;

	xhr.onreadystatechange = function (){
	    switch(xhr.readyState){
	    case 4:    // XHR com failed
		if(xhr.status == 0){
		    alert("XHR Failed");
		} else{ // XHR com success
	            if((200 <= xhr.status && xhr.status < 300) || (xhr.status == 304)){
			// alert("recv:" + xhr.responseText);
			// update_player(xhr.responseText);
			// document.loc.village.innerHTML = xhr.responseText;
			vt.innerHTML = xhr.responseText;
		    } else {// request failed
			alert("other status response:" + xhr.status);
		    } // if
		} // if
   		break;
	    } // switch
	}; // onreadystatechange
	xhr.open("POST",url,true);
	xhr.send(para);
    }
}

    function parasel_change(sel){
       var ix   = sel.selectedIndex;
       var itemname = sel.options[ix].value;
       var selname = sel.name;

       var content = sel.options[ix].innerHTML;
//       var parama  = content.split(",");
       var parama  = content.split(/[,()]+/);

       var vel = parama[3].replace(/^[A-Za-z]+=/,"");
       var tsq = parama[4].replace(/^[A-Za-z]+=/,"");
       
       document.pos.x.value   = parama[1];
       document.pos.y.value   = parama[2];

       document.pos.vel.value = vel;
       document.pos.tsq.value = tsq;
    } // function parasel_change
    
    function player_change(){
       var ix   = document.loc.player.selectedIndex;
       var name = document.loc.player.options[ix].value;

       var xhr = new XMLHttpRequest();
       var url = "http://" + "$httphost" + "/$cpath$prog/player/" + name;

       xhr.onreadystatechange = function (){
	   switch(xhr.readyState){
	   case 4:    // XHR com failed
	       if(xhr.status == 0){
		   alert("XHR Failed");
               }else{ // XHR com success
	           if((200 <= xhr.status && xhr.status < 300) || (xhr.status == 304)){
		       // alert("recv:" + xhr.responseText);
		       // update_player(xhr.responseText);
		       document.loc.village.innerHTML = xhr.responseText;
		   } else {// request failed
		       alert("other status response:" + xhr.status);
		   } // if
	       } // if
   	        break;
	   } // switch
       }; // onreadystatechange
       xhr.open("GET",url,true);
       xhr.send();
    } // function player_change


	
    function village_change(){
       var ix   = document.loc.village.selectedIndex;
       var name = document.loc.village.options[ix].value;

       var xhr = new XMLHttpRequest();
       var url = "http://" + "$httphost" + "/$cpath$prog/village/" + name;  // name = vid

       xhr.onreadystatechange = function (){
	   switch(xhr.readyState){
	   case 4:    // XHR com failed
	       if(xhr.status == 0){
		   alert("XHR Failed");
               }else{ // XHR com success
	           if((200 <= xhr.status && xhr.status < 300) || (xhr.status == 304)){
		       // alert("recv:" + xhr.responseText);
		       // update_player(xhr.responseText);
		       var posa = xhr.responseText.split(",");
		       document.pos.x.value = posa[0];
		       document.pos.y.value = posa[1];
		   } else {// request failed
		       alert("other status response:" + xhr.status);
		   } // if
	       } // if
   	        break;
	   } // switch
       }; // onreadystatechange
       xhr.open("GET",url,true);
       xhr.send();
    } // function village_change()

    function update_player(text){
	document.loc.player.innerHTML = text;
    }
    function ally_change(){
       var ix   = document.loc.ally.selectedIndex;
       var name = document.loc.ally.options[ix].value;

       var xhr = new XMLHttpRequest();
       var url = "http://" + "$httphost" + "/$cpath$prog/ally/" + name;

       xhr.onreadystatechange = function (){
	   switch(xhr.readyState){
	   case 4:    // XHR com failed
	       if(xhr.status == 0){
		   alert("XHR Failed");
               }else{ // XHR com success
	           if((200 <= xhr.status && xhr.status < 300) || (xhr.status == 304)){
		       // alert("recv:" + xhr.responseText);
		       update_player(xhr.responseText);
		   } else {// request failed
		       alert("other status response:" + xhr.status);
		   } // if
	       } // if
   	        break;
	   } // switch
       }; // onreadystatechange
       xhr.open("GET",url,true);
       xhr.send();
    } // function ally_change
    
