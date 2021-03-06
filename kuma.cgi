#!/usr/bin/perl
#
# kuma.cgi
#
# kuma DB
#
# 1. add comment
# 2. add fakelist now
# 3. add recommend
# 4. fix broken travel
# 5. remove FL from recommend in fakenow
#
# $Id$
#
use strict;

use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use CGI::Cookie;
use CGI;

use File::Basename qw(basename dirname fileparse);

use DBI;
use DBD::mysql;
use utf8;
use Encode qw (encode decode);
use LWP::UserAgent;

use FindBin;

use lib "$FindBin::Bin/lib";

use HTML::TreeBuilder;
use Time::Local;

#
# Globals
#
my $tg_aidlist = "22";
my $g_login_title = encode('utf-8', "<h1> Login : みんなの交通安全</h1>");   # external code
my $g_login;

my %msg = (
    "reserve"   => "予約",
    "fired"     => "発射済",
    "clear"     => "Cancel",
    "new"       => "新規",
    "recommend" => "推奨",
    "save"      => "保存",
    "show"      => "表示",
    "fix"       => "公開",

    "set_arrival"   => "到着時刻登録",
    "set_player"    => "プレイヤー登録",
    "set_village"   => "村登録",
    "set_grid"      => "送付元登録",
    "set_now"       => "今",
    "set_start"     => "設定",
    "set_start_plus2"     => "+2H",
    "list"          => "フォーラム用",
    "artifact"      => "秘宝",
    "capital"       => "首都",
    "fakelist"      => "fakelist",
    );

foreach my $ee (keys %msg){
    $msg{$ee} = encode('utf-8', $msg{$ee});
}

# tables for fake now
my $fakenow    = "fakenow";
my $fakeplayer = "fakeplayer";
my $fakevil    = "fakevil";
my $t_art      = "art";
my $t_capital  = "capital";
#
# 
my %faketables = (
    $fakenow    => "create table fakenow    (id serial, fid int, rev int, arrival datetime, note varchar(256), ts timestamp, unique (fid,rev)) );",
    $fakeplayer => "create table fakeplayer (id serial, fs int, uid int, enabled int, note varchar(64), ts timestamp, unique (fs,uid) );",
    $fakevil    => "create table fakevil    (id serial, fs int, vid int, enabled int, reserved varchar(64), fired varchar(64), note varchar(64), ts timestamp, unique(fs,vid) );",
    );

my $g_cookie;
my %mugiunit = (
    # Roman [rejo pre  peri lega  pera zari ram cat gi  pio hero]
    1 => [1, 1, 1, 0, 3, 4, 1, 1, 1, 1, 0],
    # Tuton [bun  spi  axe  skout para tk   ram cat gen pio hero]
    2 => [1, 0, 1, 0, 1, 3, 1, 1, 1, 1, 0],
    # Gaul  [pha  so   path tt    $    heju ram cat chi pio hero]
    3 => [0, 1, 0, 2, 0, 3, 1, 1, 1, 1, 0],
    0 => [],  # natar []
    [],
    
    );

my %mugiunit2 = (

    # Roman [rejo pre  peri lega  pera zari ram cat gi  pio hero]
    1 => [1, 1, 1, 0, 3, 4, 1, 1, 1, 1, 200],

    # Tuton [bun  spi  axe  skout para kt   ram cat gen pio hero]
    2 => [1, 0, 1, 0, 1, 3, 1, 1, 1, 1, 200],

    # Gaul  [pha  so   path tt    $    heju ram cat chi pio hero]
    3 => [15, 1, 0, 2, 0, 3, 1, 1, 1, 1, 200],
    0 => [],  # natar []
    [],
    
    );

my %spec = (
    # roman
    1 => [
	[40,35,50,"Legionaier"],
	[30, 65, 30, "Pretorian"],
	[70,40,25,"Imperian"],
	[0,20,10, "Legati"],
	[120,65,50, "Imperatoris"],
	[180, 80, 105, "Caesarius"],
	[60, 30, 75, "BatteringRam"],
	[75, 60, 10, "FireCatapalt"],
	[50, 40, 30, "Giin"],
	[0, 80, 80, "RPioneer"],
    ],
    # Tuton
    2 => [
	[40, 20, 5, "BunBun"],
	[10, 35, 60, "Spearman"],
	[60, 30, 30, "Axeman"],
	[0, 10, 5, "Skout"],
	[55, 100, 40, "Paradin"],
	[150, 50, 75, "TutonicKnight"],
	[65, 30, 80, "Ram"],
	[50, 60, 10, "Catapalt"],
	[40, 60, 40, "Gensyu"],
	[0, 80, 80, "TPioneer"],
    ],
    # gaul
    3 => [
	[15,40,50, "pharanx"], 
	[65, 35, 20, "Somen"], 
	[0,20,10,"pathfinder"],
	[90, 25, 40, "Thunder"],
	[45, 115, 55, "DruidRidar"],
	[140,60,165, "Heduan"],
	[50,30,105, "Ram"],
	[70,45,10, "Trepshe"],
	[40,50,50, "Syuryo"],
	[0,80,80,"GPioneer"],
    ],
);

#my $cpath   = "secure/";
#my $cpath   = "";

my $atinfo   = "atinfo";
my $atmugi   = "atmugi";
my $xtable   = "x_world";
my $srctable = "srcdata";

#my $kumaurl = 'http://153.126.160.254/defence?q%5Bs%5D=arrival_time+asc';
my $kumahost = '153.126.160.254';
my $kumaurl = "http://$kumahost/defence";

my $dbname = 'qshino';
my $host   = 'localhost';
my $user   = 'qshino';
my $passwd = 'f15eagle';

my $urlbase = 'http://ts4.travian.jp/position_details.php';
#my $urlbase = 'http://ts4.travian.jp/position_details.php';

my $sktable = "sk";
my $skhist  = "skhist";
my $httphost = $ENV{"HTTP_HOST"};

my $comment_table = "comment";


#show_head();

# print `perl -v`, "\n";
# print `perl -V`, "\n";
#print join(":",@INC),"\n";

#show_tail();

#exit(0);

my $chibipublic   = "/home/qshino/public_html";
my ($prog,$cpath) = fileparse $0;
$cpath =~ s!^\/!! ;
my $script = "$cpath$prog";

# my $prog = "kuma.cgi";

sub usage {
    print "kuma.pl init           : create table\n";
    print "kuma.pl reinit         : re-create table\n";

    print "kuma.pl insert <html>  : inset html into db\n";
    print "kuma.pl get            : get html from kuma site and insert\n";
    print "kuma.pl raw <html>     : show raw html\n";
    print "kuma.pl sk             : show sk table\n";

    print "kuma.pl info           : show info from sk table\n";

}

sub get_menu_item {
    my($name,$link) = @_;

    my $str = "<a href=\"/$script/$link\">$name</a>\n";
    return $str;
}

sub get_menu_item1 {
    my($name,$link) = @_;

    my $str="";
    if( $link =~ /^http/ ){
	$str = "<a href=\"$link\">$name</a>\n";
    } else {
	$str = "<a href=\"/$script/$link\">$name</a>\n";
    }
    return $str;
}

sub show_script {
    my $js = "/js/kuma3.js";
    
    print <<EOT;
    <script type=\"text/javascript\" src=\"$js\"></script>
    <script type=\"text/javascript\"> <!--  --> </script>
EOT
;
}

# auth
#   called from 
#     1. head of main  => cookie = ok => follow through, ng => authpage
#     2. Authpage      => cookie = ok => normal page, ng & pass match => normal page, ng & pass failed => Authpage
	   
sub auth {
    # my ($force) = @_;

    my $cgi = CGI->new();

    my %cookies = CGI::Cookie->fetch;
    # for (keys %cookies) {
    #   do_something($cookies{$_}); 
    # }
    my $ck;

    if( exists $cookies{"narusaid"} ){
	$ck = $cookies{"narusaid"};
	if( defined($ck) ){
	    my($login,$mark) = $ck->value;
	    #	    print join(",", @vals), "\n";
	    if ($mark eq "narusa" && defined($login) && $login ne "" ){
		$g_login = $login;
		return 0
	    }
	}
    }

    # not authed before
    my $auth = $cgi->param("auth");
    if( !defined($auth) ){
	# not from auth page
	my $c = CGI::Cookie->new(-name    =>  'narusaid',
				 -value   =>  ["login","failed"],
				 -expires =>  '+1M');
	$g_cookie = $c;
	show_auth_dialog();
	exit 0;
    }
    # from auth page
    my $login = $cgi->param("login");
    my $pw    = $cgi->param("pw");
    if( !pass_auth($login,$pw) ){
	# failed auth
	show_auth_dialog();
	exit 0;
    } else {
	# passed auth
	my $c = CGI::Cookie->new(-name    =>  'narusaid',
				 -value   =>  [$login,"narusa"],
				 -expires =>  '+1M');
	$g_cookie = $c;
	$g_login  = $login;
    }
    return 0;
}

sub pass_auth {
    my($login,$pw) = @_;

    # if ( $id eq "kuma" && $pw eq "hangeki" ){
    if ( defined($login) && $login ne "" && $pw eq "hangeki" ){
	$g_login = $login;
	return 1;
    }
    return 0;
}

sub show_auth_dialog {

    my $title = "Kotsu Anzen";

    my $c = CGI::Cookie->new(-name    =>  'narusaid',
			     -value   =>  ["failed","failed"],
			     -expires =>  '+1M');

    # http header
    # clear cookie
    print "Set-Cookie: $c\n";

    print "Content-type:text/html; charset=utf-8\n\n";

    # HTML head
    print '<html>';
    print '<head>';
    print "<title> $title </title>";
    print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/css/mana.css\">\n";
    print '</head>';

    # HTML body
    print "<body>\n";

    print $g_login_title;
    
    # login form
    print "<form method=post action=\"/$script\"/>";
    print "<p>ID: <input type=text size=16 name=login placeholder=id></p>";
    print "<p>PW: <input type=password size=16 name=pw placeholder=password></p>";
    print "<input type=hidden name=auth value=new></p>";
    print "<input type=submit name=Login>";
    print "</form>";

    print "</body></html>\n";
    
}
	   
sub show_head {
    my ($intitle) = @_;

    # update title
    my $title = "Dance with KumaHome";
    $title = "援軍発射時刻計算機";
    if( defined($intitle) ){
	$title = $intitle;
    }
    $title = encode('utf-8', $title); # for output
    #
    # show head
    #
    # handle auth
    if ( defined($g_cookie) ){
	print "Set-Cookie: $g_cookie\n";
    }

    # other header
    print "Content-type:text/html; charset=utf-8\n\n";
    print '<html>';
    print '<head>';
    print "<title> $title </title>";

    print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/css/mana.css\">\n";
    print "<link rel=\"stylesheet\" type=\"text/css\" href=\"/css/style.css\">\n";
    print "<script type=\"text/javascript\" src=\"/js/script.js\"></script>";

    print '</head>';
    print '<body>';
    print "\n";

    show_script();

    print "<div class=top>";
    print "<h1> $title </h1>\n";

    my %menulabels = (
	"load_narusa" => "データロード",
	"other_sites" => "他サイト",
	"for_debug"   => "デバック用",
	);
    

    ### menu area
    print "<div class=menu>";
    print "<table><tr>";
    my @menuitems = qw(-- show atinfo armlog fakenow fakelist artifact travel -- login ||other_sites ,narusa,http://153.126.160.254/defence ||load_narusa load_narusa ||for_debug sk update_atinfo ||);

    print "<td>$g_login</td>";

    foreach my $item (@menuitems){
	if( $item eq "--" || $item eq "||"){
	    # separator
	    print "<td>||$item</td>";
	} elsif( $item =~ /^\|\|/ ){
	    # label
	    $item =~ s/^\|\|//;
	    my $msg = encode('utf-8', $menulabels{$item});
	    print "<td>||$msg</td>";
	} elsif( $item =~ /^,/ ){
	    # name and link
	    my($blank,$name,$link) = split(/,/,$item);
	    print "<td>||", get_menu_item1($name,$link), "</td>";
	} else {
	    # link
	    print "<td>||", get_menu_item1($item,$item), "</td>";
	}
    }
    print "</tr></table>\n";
    print "</div>";
    print "</div>";
}

sub show_tail {
    print "<hr>";
    #    print "prog=$prog dir=$dirname";
    print "Copyright(C) 2016, zolo All rights reserved.";
    print '</body>';
    print '</html>';
}

sub open_db {
    my $db = DBI->connect("DBI:mysql:$dbname:$host", $user, $passwd,
		 { mysql_enable_utf8 => 1 , # 結果をUTF8フラグ付きにする（MySQL）
		 });
    return $db;
}

sub close_db {
    my($db) = @_;

    return $db->disconnect;
}

sub run_sql {
    my($q) = @_;

    my $db = open_db();
    
    my $sth = $db->prepare($q);
    $sth->execute();
    $db->commit();

    close_db($db);

    return $sth;
}

sub do_sql {
    my($db, $q) = @_;

    my $sth = $db->prepare($q);
    $sth->execute();
#    $db->commit();

    return $sth;
}

sub show_data_table {
    my($sth,$idname, $func) = @_;
    
    my $num_rows = $sth->rows;
    
    print "Found $num_rows rows<br>\n";
    if( !defined($idname) ){
	print "<table class=bstyle>\n";
    } else {
	print "<table $idname>\n";
    }
    my $title_ap = $sth->{NAME};
    #
    # show table header
    #
    print "<thead>"; print "<tr>";
    foreach my $hh (@$title_ap){ print "<th>$hh</th>\n"; }
    print "</tr>"; print "</thead>";

    my $eo = "class=even";
    print "<tbody>";

    for (my $i=0; $i<$num_rows; $i++) {
	my @a = $sth->fetchrow_array;
	print "<tr $eo>";
	$eo = ($eo ne "class=even" )?"class=even":"";
	if( defined($func) ){ @a = &$func($i,\@a);}
	foreach my $x (@a){ print "<td>$x</td>"; }
	print "</tr>\n";
    }
    print "</tbody>";
    print "</table>\n";
    $sth->finish;

    return $num_rows;
}

sub get {
    my($url) = @_;

    my $ua = LWP::UserAgent->new();

    $ua->timeout(30);
    $ua->agent('Mozilla');

    #GET、PUT、POST、DELETE、HEADのいずれかを指定（httpsの場合はhttpsにするだけ）
    my $req = HTTP::Request->new(GET => $url);

    my $user = 'kuma';
    my $pw = 'hangeki';

    $req->authorization_basic($user,$pw);

    #リクエスト結果を取得
    #requestメソッドではリダイレクトも自動的に処理するため、そうしたくない場合はsimple_requestメソッドを使用するとよい。
    my $res = $ua->request($req);

    #is_successの他にis_redirect、is_errorなどがある(is_redirectを判定する場合、simple_requestメソッドを使用)
    if ($res->is_success) {
	return $res->content;
    }
    else{
	return $res->status_line . "\n";
    }    
}

sub show_html {
    my($url) = @_;

    my $ret = 0;
    
    my $html = get($url);
    print $html;
    return $ret;
}

sub to_xy {
    my($grid) = @_;

    my($space,$x,$y) = split(/[\(\)\|]/,$grid);
    return ($x,$y);
}

sub datestring {
    my ($tserial) = @_;

    my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst)
	= localtime($tserial);
    $year += 1900;
    $mon += 1;

    return sprintf "%04d-%02d-%02d %02d:%02d:%02d",$year,$mon,$mday,$hour,$min,$sec;
}
    
sub to_date_string {
    my($dd,$year) = @_;

    my ($mm, $dd,$tt) = split(/[\s\/]/,$dd);
    
    return sprintf "%04d-%02d-%02d %s", $year, $mm, $dd, $tt;
}

sub to_date {
    my($dd,$year) = @_;

    my ($mm, $dd,$tt) = split(/[\s\/]/,$dd);
    
    return sprintf "%04d-%02d-%02d %s", $year, $mm, $dd, $tt;
}

sub to_time_serial {
    my($dtime) = @_;

    # $dtime format  YYYY-MM-DD HH:MM:SS
    my($y,$mon,$d,$h,$min,$s) = split(/[-\s:]/,$dtime);
    my $serial = timelocal($s,$min,$h, $d, $mon-1, $y-1900);

    return $serial;
}

sub do_parse_html {
    my($html) = @_;

    my $root = HTML::TreeBuilder->new_from_content($html);
    return do_parse_root($root);
}

sub do_parse_file {
    my($filename) = @_;

    print "Parsing $filename\n";
    my $root = HTML::TreeBuilder->new_from_file($filename);
    #    $root->dump();
    return do_parse_root($root);
}

sub find_next {
    my($root) = @_;

    my $next = undef;
    my $li_next = $root->find_by_attribute('class', 'next');
    return undef if (!defined($li_next));
    my $a_next  = $li_next->find('a');
    return undef if ($a_next == undef );
    my $uri     = $a_next->attr('href');

    return "http://$kumahost$uri";
}

sub do_parse_root {
    my($root) = @_;

    my $nexturl = find_next($root);

    my $tbody = $root->find("tbody");
    return ([], $nexturl) if ( !defined($tbody) );
    my @rows  = $tbody->find("tr");
    
    my @lists = ();

    foreach my $row (@rows){
	my @cols = $row->find("td");

	my $dp = [];
	
	foreach my $col (@cols){
	    my $aref = $col->attr("_content");

	    foreach my $el (@$aref){
		if (ref $el ){
		    my $ap = $el->attr("_content");
		    push @$dp, $ap->[0];
		} else {
		    push @$dp, $el;
		}
	    }
	}
	push @lists, $dp;
    }
    return (\@lists, $nexturl);
}

sub show_raw_data {
    my ($lp) = @_;

    foreach my $ee (@$lp){
	print join(",", @$ee), "\n";
    }
}

sub show_data {
    my ($lp) = @_;

    my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst)
	= localtime(time);
    $year += 1900;
    $mon += 1;

    my $regtime = "$year-$mon-$mday $hour:$min:$sec";

    foreach my $ee (@$lp){
	#	print join('-', @$ee), "\n";
	#	print $ee->[7], $ee->[8],"\n";
	my($sx,$sy) = to_xy($ee->[3]);
	my($dx,$dy) = to_xy($ee->[7]);
	my($dtime)  = to_date_string($ee->[8], $year);
	my($stime)  = to_date_string($ee->[9], $year);

	my @atdata = (0,1,2);
	my @dfdata = (4,5,6);
	
	my $at    = "";
	my $df    = "";
	my $note  = "";

	foreach my $x (@atdata){ $at .= $ee->[$x] . ","; }
	foreach my $x (@dfdata){ $df .= $ee->[$x] . ","; }
	
#	print "sx=$sx,sy=$sy,dx=$dx,dy=$dy,$dtime,$stime\n";

	print "insert into sk (sx,sy,dx,dy,dtime,stime,regtime,note) values ($sx,$sy,$dx,$dy,\'$dtime\',\'$stime\',\'$regtime\',\'$note\');\n";
    }
    return 0;
}

#
# step
#  0 first and last
#  1 first but last
#  2 second but last
#  3 last
#
sub insert_data {
    my ($lp, $continue) = @_;
    
    my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst)
	= localtime(time);
    $year += 1900;
    $mon += 1;

    my $regtime = "$year-$mon-$mday $hour:$min:$sec";

    my $db = open_db();

    # print "DBG: insert_data with cont=$continue\n";
    
    # for first (none, 0, 1)
    if( !defined($continue) || !$continue || $continue == 1){
	# print "truncating $sktable\n";
	do_sql($db, "truncate table $sktable;");
    }
    
    foreach my $ee (@$lp){
	my($sx,$sy) = to_xy($ee->[3]);
	my($dx,$dy) = to_xy($ee->[7]);
	my($dtime)  = to_date($ee->[8], $year);
	my($stime)  = to_date($ee->[9], $year);

	my @atdata = (0,1,2);
	my @dfdata = (4,5,6);
	
	my $at    = "";
	my $df    = "";
	my $note  = "";

	foreach my $x (@atdata){ $at .= $ee->[$x] . ","; }
	foreach my $x (@dfdata){ $df .= $ee->[$x] . ","; }

	my $sql = "insert into $sktable (sx,sy,dx,dy,dtime,stime,regtime,at,df,note) values ($sx,$sy,$dx,$dy,\'$dtime\',\'$stime\',\'$regtime\', \'$at\', \'$df\', \'$note\');";

	do_sql($db, $sql);
    }

    # last
    # none 0, 3
    if ( !defined($continue) || !$continue || $continue == 3 ){
	my $sth = do_sql($db, "select count(*) from $sktable;");
    
	my ($cnt) = $sth->fetchrow_array;
	$sth = do_sql($db, "insert into $skhist (cnt) values ($cnt);");
	$sth->finish;
    }
    
    close_db($db);

    return 0;
}

sub dist {
    my($ax,$ay,$bx,$by) = @_;

    return ( ($ax-$bx)**2 + ($ay-$by)**2) ** 0.5;
}

sub hours {
    my($d, $vel, $tsq ) = @_;

    if ( $d <= 20 ){ return $d/$vel;}
    
    return ($d-20)/($vel * (1+$tsq/10.0)) + 20.0/$vel ;
}

sub show_last_comment {

    my $db = open_db();

    my $sth = do_sql($db, "select who,comment from $comment_table order by id desc;");
    my $num_rows = $sth->rows;

    print "<table class=bstyle>\n";
    for(my $i=0; $i<$num_rows;$i++){
	print "<tr>";
	my ($who,$com) = $sth->fetchrow_array;
	print "<td>$who</td><td align=left>$com</td>\n";
	print "</tr>";
    }
    print "</table>\n";

    $sth->finish;
    close_db($db);
}

sub show_comment_form {
    print "<form method=post action=/$script/comment>\n";

    print "<p><input type=text name=who placeholder=name></p>\n";
    print "<p><textarea name=comment cols=80 rows=6 placeholder=content></textarea></p>\n";
    print "<input type=submit name=go value=Send>\n";

    print "</form>\n";
}

sub do_comment {

    my $cgi = CGI->new();
    my $comment = $cgi->param("comment");
    my $who     = $cgi->param("who");

    my $db = open_db();
    my $sth = do_sql($db, "insert into $comment_table (who,comment) values (\'$who\', \'$comment\'); ");
    $sth->finish;
    close_db($db);
}

sub show_form {
    my($x,$y,$tsq,$vel) = @_;
    my $action = "/$script/show";
    return show_form_action($x,$y,$tsq,$vel, $action);
}

sub show_form_action {
    my($x,$y,$tsq,$vel, $action) = @_;

    #    print "送付元：";
    if( $action ){
	print "<form name=pos method=post action=$action>\n";
    }

    print "x: <input id=xx type=text size=5 name=x value=$x>\n";
    print "y: <input id~yy type=text size=5 name=y value=$y>\n";
    print "Velocity: <input id=vel type=text size=5 name=vel value=$vel>\n";
    print "Tournament Square Level: <input id=tsq type=text size=5 name=tsq value=$tsq>\n";

    print "<input type=submit name=go value=show>\n";

    if( $action ){
	print "</form>\n";
    }
}


sub show_form_sel {
    my($db,$x, $y, $vel,$tsq) = @_;
    return show_form_sel_sub($db,$x, $y, $vel,$tsq, "/$script/show");
}


sub show_form_sel_sub {
    my($db,$x, $y, $vel,$tsq, $action) = @_;

    # ally, player, village, vel, tsq
    my($uid,$user,$vid, $village, $aid,$alliance) = (-1,"",-1,"",-1,"");

    my $sth = do_sql($db, "select x,y,uid,user,vid, village, aid,alliance from x_world where x = $x and y = $y;");
    my $matched = $sth->rows;
    if( $matched > 0 ){
	my ($ax,$ay);
	($ax, $ay, $uid, $user, $vid, $village, $aid, $alliance) = $sth->fetchrow_array;
    }
    $sth->finish;

    if( $action ){
	print "<form style=\"float:left;\" name=loc method=post action=$action>\n";
    }
    print "送付元：";

    print "<select name=ally onclick=ally_change()>\n";

    $sth = do_sql($db, "select aid,alliance from $xtable where aid > 0 group by alliance order by sum(population) desc limit 10;\n");
    my $num = $sth->rows;
    for(my $i; $i< $num; $i++){
	my($xaid, $ally) = $sth->fetchrow_array;
	my $mark = "";
	$mark = "selected" if ( $xaid == $aid );
	print "<option value=$xaid $mark>$ally</option>\n";
    }
    print "</select>\n";

    print "<select name=player onclick=player_change()>\n";
    if( $uid > 0 ){
	$sth = do_sql($db, "select uid,user from $xtable where aid = $aid group by uid,user;");
	my $num = $sth->rows;
	for(my $ix=0;$ix<$num;$ix++){
	    my($xuid,$xuser) = $sth->fetchrow_array;
	    my $mark = ($xuid == $uid)?"selected":"";
	    print "<option value=$xuid $mark>$xuser</option>\n";
	}
    }
    print "</select>\n";
    #
    # X,Y,Vel,TSQ Selector
    #
    print "<select name=village onclick=village_change()>\n";
    if( $vid > 0 && $uid > 0 ){
	$sth = do_sql($db, "select vid,village from $xtable where uid = $uid;");
	my $num = $sth->rows;
	for(my $ix=0;$ix<$num;$ix++){
	    my($xvid,$xvillage) = $sth->fetchrow_array;
	    my $mark = ($xvid == $vid)?"selected":"";
	    print "<option value=$xvid $mark>$xvillage</option>\n";
	}
    }
    print "</select>\n";
    if( $action ){
	print "</form>\n";
    }
}

sub show_form_params {
    my ($db, $x, $y, $vel, $tsq) = @_;
    # 
    # get params from $srctable
    #
    my ($sid) = $db->selectrow_array("select id from $srctable where x = $x and y = $y and vel = $vel and tsq = $tsq;");

    $sid = 0 if (!defined($sid));

    print "<select name=params onclick=parasel_change(this)>\n";

    my $sth = do_sql($db, "select id, x, y, vel, tsq from $srctable;");
    my $num = $sth->rows;
    for(my $ix=0;$ix<$num;$ix++){
	my($id,$x,$y,$vel,$tsq) = $sth->fetchrow_array;
	my $mark = "";
	$mark = "selected" if( $id == $sid );
#	print "<option value=$id>$x,$y,$vel,$tsq</option>\n";
	print "<option value=$id $mark>($x,$y),vel=$vel,tsq=$tsq</option>\n";
    }
    print "</select>\n";
    print "";
}

sub show_snip_form {
    my($skid, $x,$y, $vel, $tsq) = @_;

    print "送付元：";
    print "<form method=post action=/$cpath$prog/snip/$skid/last>\n";

    print "x: <input type=text size=5 name=x value=$x>\n";
    print "y: <input type=text size=5 name=y value=$y>\n";
    print "Velocity: <input type=text size=5 name=vel value=$vel>\n";
    print "Tournament Square Level: <input type=text size=5 name=tsq value=$tsq>\n";

    print "<input type=submit name=go value=calc>\n";

    print "</form>\n";
}

sub to_sdur {
    my($secs) = @_;

    my $sec   = $secs % 60;
    my $mins  = int($secs/60);
    my $min   = $mins % 60;
    my $hours = int($mins / 60);

    return "$hours:$min:$sec";
}

sub location {
    my($x,$y) = @_;

    return "<a href=\"$urlbase?x=$x&y=$y\">($x,$y)</a>";
}

sub player {
    my($uid,$user) = @_;

    my $site = 'http://ts4.travian.jp';
    
    return "<a href=\"$site/spieler.php?uid=$uid\">$user</a>";

# my $urlbase = 'http://ts4.travian.jp/position_details.php';
# http://ts4.travian.jp/spieler.php?uid=167    

}

#
# return
#   1 matched
#   0 not matched
#
sub cmp_wave {
    my($a, $b) = @_;

    # (sx,sy,dx,dy,dtime) <-> (1,2,3,4,5)
    my @ixa = (1,2,3,4,5);

    foreach my $ix (@ixa){
	return 0 if ( $a->[$ix] != $b->[$ix] );
    }
    return 1;
}

sub show_skhist {
    my($db) = @_;

    my $sth = do_sql($db, "select * from $skhist order by id desc limit 5;");

    print "<table class=bstyle>\n";

    my @tp = qw( id #waves updated );

    print "<tr>";
    print join("", map {"<th>" . $_ . "</th>" } @tp );
    print "</tr>\n";
    
    my $num_rows = $sth->rows;
    for(my $i; $i< $num_rows;$i++){
	print "<tr>\n";
	my @cols = $sth->fetchrow_array;
	print join("", map {"<td>".$_."</td>"} @cols);
	print "</tr>\n";
    }
    print "</table>\n";
    
    
}

sub register_srcdata {
    my($db, $x,$y,$tsq,$vel) = @_;

    my $sth = do_sql($db, "insert into $srctable (x,y,tsq,vel) values ($x,$y,$tsq,$vel);");
    $sth->finish;
}

sub get_id_srcdata {
    my($db, $x,$y,$tsq,$vel) = @_;

    my $sth = do_sql($db, "select id from $srctable where x = $x and y = $y and tsq = $tsq and vel = $vel;");

    my ($id) = $sth->fetchrow_array;

    $sth->finish;
    return $id;
}


sub show_atinfo {

    my %arts;
    
    my $db = open_db();

    # get S/U artifact
    my $q   = "select x.uid, a.name from art a join $xtable x on a.x = x.x and a.y = x.y where a.bronz = 0;";
    my $sth = do_sql($db, $q);
    $sth->execute;
    my $num = $sth->rows;

    for(my $ix=0;$ix<$num;$ix++){
	my($uid,$artname) = $sth->fetchrow_array();
	if( defined($arts{$uid}) ){
	    my $ap = $arts{$uid};
	    push @$ap, $artname;
	} else {
	    $arts{$uid} = [$artname];
	}
    }

    # scan at history
    $sth = do_sql($db,"select a.id, x.x, x.y, x.uid, x.user, a.stime, a.dtime, a.waves,x.village, c.uid iscapital, t.name from $atinfo a join $xtable x on a.sx = x.x and a.sy = x.y left outer join capital c on a.sx = c.x and a.sy = c.y left outer join art t on a.sx = t.x and a.sy = t.y order by x.uid, a.stime desc;");

    $num = $sth->rows;
    print "<table class=bstyle>\n";
    my @head = qw(Player Waves Start Arrival Location Village Capital Artifact US_Artifact);

    print "<tr>";
    print join("", map {"<th>".$_."</th>"} @head);
    print "</tr>";

    my $eo = "";
    
    for(my $ix=0;$ix<$num;$ix++){
	my($id,$x,$y,$uid,$user,$stime,$dtime,$waves, $village, $uidcap, $art) = $sth->fetchrow_array;
	my $loc = location($x,$y);

	$eo = ($eo eq "even")?"":"even";
	print "<tr class=\"$eo\">";
	
	my $player = player($uid,$user);
	print "<td>$player</td>";
	print "<td align=center>$waves</td>";

	my $nstime = dnormal($stime);
	my $ndtime = dnormal($dtime);

	print "<td>$nstime</td>";
	print "<td>$ndtime</td>";
	print "<td>$loc</td>";
	print "<td>$village</td>";
	my $iscap = ($uidcap>0)?"Capital":"";
	print "<td>$iscap</td>";
	print "<td>$art</td>";

	my $ap = [];
	$ap = $arts{$uid} if(defined($arts{$uid}));
	my $sart = join(",", @$ap);
	print "<td>$sart</td>";
	print "</tr>";
    }
    print "</table>\n";
    $sth->finish;

    close_db($db);
}

# date normal
sub dnormal {
    my($date) = @_;

    $date =~ s/2016-//;
    return $date;
}

#
# show_fakenow();
#

#
# Functions for fakelist
#
#   1. Set target arrival
#   2. Set Source
#   3. Set players
#   4. Set village
#   5. fix  : set fixed mark
#   6. next : create next fakelist
#
# Functions for fakenow
#
#   a. reserve
#   b. fired
#
# fakenow table
#   create table fakenow (id serial, rev int, arrival datetime, note varchar(256) );
#
sub init_fakenow {
    my ($db) = @_;

    my $ret = reinit_tables($db, \%faketables);
    return $ret;
}

sub reinit_tables {
    my ($db, $hp) = @_;

    my $ret = 0;
    
    foreach my $name (keys %$hp){
	my $ct = $hp->{$name};

	my $sql = "select 1 from $name";
	my $ret = $db->selectrow_array($sql);

	# print "DBG:reinit_tables: name=$name, ret=$ret\n";

	if( !defined($ret) ){
	    # not exists
	    $ret = $db->do($ct);
	}
    }
    return $ret;
}

sub update_or_insert_fakevil {
    my($db,$fs,$resv,$fired, @vils) = @_;

    my $ret = 0;
    # insert will fail when row exists because of (fs,vid) unique constraint
    foreach my $vid (@vils){
	my $sql = "insert into $fakevil (fs,vid,reserved,fired) values ($fs,$vid,\"$resv\",\"$fired\");";

	# print "DBG; insert: $sql\n";
	$ret = $db->do($sql);
    }

    $resv  = "null" if( !defined($resv)  || $resv eq "" );
    $fired = "null" if( !defined($fired) || $fired eq "" );

    my $vlist = join(",", @vils);
    
    my $updr = "update $fakevil set reserved = \"$resv\" where fs = $fs and vid in ($vlist);";
    my $updf = "update $fakevil set fired = \"$fired\" where fs = $fs and vid in ($vlist);";
    my $updb = "update $fakevil set reserved = null, fired = null where fs = $fs and vid in ($vlist);";
    
    # anyway try to update.
    my $upd;
    if( $resv ne "null" ) {
	# update reserved
	$upd = $updr;
    } elsif( $fired ne "null" ) {
	# update fired
	$upd = $updf;
    } else {
	# clear
	$upd = $updb;
    }
    # print "DBG: update: $upd\n";
    $ret = $db->do($upd);

    return $ret;
}

#
#  Priority : cgi -> DB -> inpar
#
#  1. valid cgi x,y -> CGI
#  2. else valid DB -> DB
#  3. else inpara
#

sub get_location_by_login {
    my($db, $cgi, $login, $x, $y) = @_;

    my $cx = $cgi->param("x");
    my $cy = $cgi->param("y");

    if( defined($cx) && defined($cy) ){
	return ($cx, $cy);
    }

    if( !defined($login) || $login eq "" || $login eq "unknown" ){
	# print "DBG: fail 1 $login, $x, $y\n";
	return ($x,$y);
    }
    my $internal_login = decode('utf-8', $login);
    my($ox,$oy) = $db->selectrow_array("select c.x, c.y from capital c join last l on c.x = l.x and c.y = l.y where l.user = \"$internal_login\";");
    if( !defined($x) || !defined($y) ){
	# print "DBG: fail 2 $login, $ox, $oy, $x, $y\n";
	return ($x,$y);
    }
    return ($ox,$oy);
}

sub exec_fakenow {
    my($db, $cgi, $x,$y,$vel,$tsq) = @_;

    my($exec,$cid,$cfid,$crev) = fakelist_get_cgi_param($cgi);
    my $username = $g_login; $username = "unknown" if( $g_login eq "");

    my $ret = 0;

    if( defined($exec) ){
	# print "exec ";
	if( $exec eq $msg{"reserve"} ){
	    # reserve
	    # print "-- reserve -- cid:$cid, cfid:$cfid, crev:$crev, login:$g_login ";
	    my @vils = $cgi->param("village");

	    $ret = update_or_insert_fakevil($db, $cid, $username, "", @vils);
	} elsif( $exec eq $msg{"fired"} ){
	    # fire
	    # print "-- fire -- $cid, $cfid, $crev ";

	    my @vils = $cgi->param("village");
	    $ret = update_or_insert_fakevil($db, $cid, "", $username, @vils);

	} elsif( $exec eq $msg{"clear"} ){
	    # clear
	    # print "-- clear -- $cid, $cfid, $crev ";

	    my @vils = $cgi->param("village");
	    $ret = update_or_insert_fakevil($db, $cid, "", "", @vils);
	} elsif( $exec eq $msg{"set_now"} ){
	    my $now = datestring(time());
	    $cgi->param(-name => "start", -value => $now);
	} elsif( $exec eq $msg{"set_start"} ){
	    # my $now = datestring(time());
	    # $cgi->param(-name => "start", -value => $now);
	    1;
	} elsif( $exec eq $msg{"set_start_plus2"} ){
	    my $dt = time();
	    my $start = $cgi->param("start");
	    if( defined($start) && $start ){
		$dt = to_time_serial($start);
	    }
	    $dt += 3600*2;
	    $cgi->param(-name => "start", -value => datestring($dt));
	}
    }
    return show_fakenow($db,$cgi, $x,$y,$vel,$tsq);
}

sub sortable_control {
    my($svar, $curid, $pagelimitid, $contid, $perpageid, $naviid) = @_;

    print <<EOT
	<div id=\"$contid\" class="controls_class">
		<div id=\"$perpageid\" class="perpage_class">
			<select onclick="$svar.size(this.value)">
			<option value="5">5</option>
				<option value="10">10</option>
				<option value="30" selected="selected">30</option>
				<option value="50">50</option>
				<option value="100">100</option>
			</select>
			<span>Entries Per Page</span>
		</div>
		<div id=\"$naviid\" class="navigation_class">
			<img src="/css/images/first.gif" width="16" height="16" alt="First Page" onclick="$svar.move(-1,true)" />
			<img src="/css/images/previous.gif" width="16" height="16" alt="First Page" onclick="$svar.move(-1)" />
			<img src="/css/images/next.gif" width="16" height="16" alt="First Page" onclick="$svar.move(1)" />
			<img src="/css/images/last.gif" width="16" height="16" alt="Last Page" onclick="$svar.move(1,true)" />
		</div>
		<div class="sortable_text_class">Displaying Page <span id=\"$curid\"></span> of <span id=\"$pagelimitid\"></span></div>
	</div>
EOT
;

}

sub sortable_init {
    my($svar, $curid, $pagelimitid, $tableid) = @_;

    print <<EOT
    <script type="text/javascript">
    <!--
        var $svar = new TINY.table.sorter(\'$svar\');
        $svar.head = 'head'; //header class name
	$svar.asc = 'asc'; //ascending header class name
	$svar.desc = 'desc'; //descending header class name
	$svar.even = 'evenrow'; //even row class name
	$svar.odd = 'oddrow'; //odd row class name
	$svar.evensel = 'evenselected'; //selected column even class
	$svar.oddsel = 'oddselected'; //selected column odd class
	$svar.paginate = true ; //toggle for pagination logic
	$svar.pagesize = 30 ; //toggle for pagination logic
	
	$svar.currentid = \'$curid\'; //current page id
	$svar.limitid = \'$pagelimitid\'; //page limit id

	$svar.init(\'$tableid\',1);
    -->
    </script>
EOT
;	
}

sub fakenow_show_with_div {
    my($db, $filtername, $filtervalue, $ix, $selc, $fromc, $condc ) = @_;

    return fakenow_show_with_div_sql($db, $filtername, $filtervalue, $ix, $selc . $fromc . $condc );
}
	
 sub fakenow_show_with_div_sql {
    my($db, $filtername, $filtervalue, $ix, $sql ) = @_;

    my $divid = "vt_${filtername}_${filtervalue}";
    print "<div id=$divid>";

    fakenow_show($db, $filtername, $filtervalue, $ix, $sql, "", "" );
    print "</div>\n";
}

#
# fakenow_show()
#
sub fakenow_show {
    my($db, $filtername, $filtervalue, $ix, $selc, $fromc, $condc ) = @_;

    my $title = get_div_title($db, $filtername, $filtervalue);

    my $sqlvil = $selc . $fromc . $condc;
    # print "DBG: $sqlvil\n";
    
    print "<h3>$title</h3>";

    # print "<p>DBG: $sqlvil</p>\n";
    my $sth = do_sql($db, $sqlvil);
    show_data_table($sth, "id=gvil$ix class=sortable");

    sortable_control("sorter$ix", "currentpage$ix", "pagelimit$ix", "controls$ix", "perpage$ix", "navigation$ix");
    sortable_init(   "sorter$ix", "currentpage$ix", "pagelimit$ix", "gvil$ix");

    return 0;
}

# get_recommend()
#
# 1. artifact
# 2. villages in fakeplayers
#
sub get_recommend {
    my ($db, $id, $nart, $nvil, $selc, $rest) = @_;

    # fakevil
    my $uf = " $selc from $fakevil f join last l on l.vid = f.vid \
               left outer join $t_capital c on c.x = l.x and c.y = l.y \
               left outer join $t_art a     on a.x = l.x and a.y = l.y \
               where f.fs = $id ";

    if( !defined($nart) ){$nart = 5;}
    if( !defined($nvil) ){$nvil = 3;}
    $nart = 5; $nvil = 2;

    # artifact
    my $ua = " $selc \
               from $t_art a join last l on a.x = l.x and a.y = l.y \ 
                 left outer join $t_capital c on c.x = l.x and c.y = l.y \
                 left outer join $fakevil f on f.vid = l.vid and f.fs = $id \
               where l.aid = ($tg_aidlist) and f.vid is null \
               order by abs($rest) asc \
               limit $nart ";

    # fakeplayer capital and artifact
    my $uca = "  $selc from $fakeplayer p join last l on l.uid = p.uid and p.fs = $id \
                   join $t_capital c on c.x = l.x and c.y = l.y \
                   left outer join $t_art a on a.x = l.x and a.y = l.y \
                   left outer join $fakevil f on f.vid = l.vid and f.fs = $id \
               where f.vid is null and p.uid is not null \
                   and (c.x is not null or a.x is not null )";

    my @uva = ();
    
    my $sth = do_sql($db, "select uid from $fakeplayer where fs = $id;");
    my $nrows = $sth->rows();
    for(my $ix=0;$ix<$nrows;$ix++){
	my ($uid) = $sth->fetchrow_array();
	my $uv = " $selc from $fakeplayer p join last l on l.uid = p.uid \
                 left outer join $t_capital c on c.x = l.x and c.y = l.y \
                 left outer join $t_art a on a.x = l.x and a.y = l.y \
                 left outer join $fakevil f on f.vid = l.vid and f.fs = $id \
               where p.uid = $uid and f.vid is null \
                 and c.x is null and a.x is null \
               order by abs($rest) asc limit $nvil ";
	push @uva, "($uv)";
    }
    my $uvlist = join(" union ", @uva);
    # my $uvlist = pop @uva;
    my $uv0 = " $selc from $fakeplayer p join last l on l.uid = p.uid \
                 join $t_capital c on c.x = l.x and c.y = l.y \
                 left outer join $t_art a on a.x = l.x and a.y = l.y \
                 left outer join $fakevil f on f.vid = l.vid and f.fs = $id \
               where p.uid is not null and f.vid is null and ( c.x is null and a.x is null ) \
               order by abs($rest) asc limit $nvil ";

    # return "$uca";
    # fakelist, artifact, capital and village in fakeplayers
    return "($ua) union ($uca) union $uvlist";
    # return "($uf) union ($ua) union ($uca) union $uvlist";
}

#
# add margin
#
sub show_fakenow {
    my($db, $cgi, $x,$y,$vel,$tsq) = @_;

    init_fakenow($db);

    my $start  = $cgi->param("start");
    if( !defined($start) || $start =~ /^\s*$/ ){
	# print "current start time = $start\n";
	$start = datestring(time());
    }
    
    my $margin = $cgi->param("margin");
    $margin = 2 if( !defined($margin));

    my $sql = "select id, fid, rev, arrival, nart, nvil from $fakenow where fixed > 0 order by fid desc, rev desc limit 1;";
    my ($id,$fid,$rev,$arrival, $nart, $nvil) = $db->selectrow_array($sql);
    my $nvil--; # nvil include capital. So, decrese capital

    if( !defined($id) ){
	$id = 0; $rev = 0;
	$arrival = datestring(time() + 3600*24); # 1 day later as default
    }

    ($x,$y)   = get_location_by_login($db, $cgi, $g_login, $x, $y);

    print "<form method=post action=/$script/fakenow/exec>\n";
    #
    # Top div
    #
    print "<div>";
    print "<table border=0>";

    # Flight and arrival
    print "<tr>";

    print "<td>Flight $fid</td><td>Rev. $rev (SN=$id)</td>";
    print "<td>Arrival</td><td><b color=red>$arrival</b></td>";

    # margin and start
    print "<td>Margin(hour)</td><td>";
    print "<input id=margin type=text size=4 name=margin value=$margin>";
    print "</td>";

    # source location
    print "<td>X</td><td><input id=xx type=text size=5 name=x value=$x></td>";
    print "<td>Y</td><td><input id=yy type=text size=5 name=y value=$y></td>";
    print "<td>VEL</td><td><input id=vel type=text size=5 name=vel value=$vel></td>";
    print "<td>TSQ</td><td><input id=tsq type=text size=5 name=tsq value=$tsq></td>";

    print "</tr>";
    print "</table>";

    print "<p>";
    print "<b>Start:</b><input id=start type=text name=start value=\"$start\">";
    print "<input type=submit name=exec value=$msg{set_start}>";
    print "<input type=submit name=exec value=$msg{set_now}>";
    print "<input type=submit name=exec value=$msg{set_start_plus2}>";
    print "<span style=\"width: 20px;\"></span><span>Fake village: </span>";
    print "<input type=submit name=exec value=$msg{reserve}>";
    print "<input type=submit name=exec value=$msg{fired}>";
    print "<input type=submit name=exec value=$msg{clear}>";
    print "</p>";

    print "<input id=arrival type=hidden name=harrival value=\"$arrival\">";
    print "<input id=id type=hidden name=id value=$id>\n";
    print "<input id=fid type=hidden name=fid value=$fid>\n";
    print "<input id=rev type=hidden name=rev value=$rev>\n";

    print "</div>";

    #
    # left div
    #
    print "<div style=\"float:left;\">";
    #
    # for table categories
    #
    print "<div>";   # begin category div
    print "<table class=bstyle>";

    my @filters = qw(all recommend fakelist intime artifact capital);
    print "<tr><th>Filters</th><th>chk</th></tr>\n";
    foreach my $filter (@filters){
	print "<tr><td>$filter</td><td><input type=checkbox name=filter value=$filter checked onclick=\"filter_change(this)\"></td></tr>\n";
    }
    print "</table>";
    print "</div>";  # end category div
    #
    # For player div
    #
    print "<div>";   # begin players div
    # players list: username checkbox
    $sql = "select user, concat('<input type=checkbox name=player value=', uid, ' onclick=filter_change(this)>') chk from last l where aid = 22 group by uid order by sum(population) desc;";
    my $sth = do_sql($db, $sql);
    show_data_table($sth);
    print "</div>\n"; # end players div
    #
    #
    print "</div>";     # for left div
    #
    # SPACER div
    #
    print "<div style=\"float:left;width=20px;\"></div>";
    #
    # right div
    #
    print "<div id=\"vtables\" style=\"float:left;vertical-align:top;\">";

    my $dist     = "dist($x,$y,l.x,l.y)";
    my $travel   = "travel($dist, $vel, $tsq)";                          # travel hours
    my $rest     = "TIMESTAMPDIFF(second, \"$start\", \"$arrival\")";    # rest seconds
    
    my $intimem  = "( $rest >= ( $travel - $margin ) * 3600)";
    my $intime   = "( $rest >= $travel * 3600 )";

    my $selc  = get_selc($arrival, $x, $y, $vel, $tsq, $margin, $start);
    
    # for general
    my $fromc .= " from last l left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $fromc    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    # for artifact
    my $fromc2 .= " from $t_art a join last l on a.x = l.x and a.y = l.y ";
    $fromc2    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    # aid condition
    my $cond_aid     = " where (l.aid in ($tg_aidlist)) ";
    # for fakelist
    my $cond_fl      = " $cond_aid and ( f.fs = $id and f.enabled > 0 ) ";
    # for inttime
    my $cond_intime  = " $cond_aid and ( $intimem ) ";

    # other clauses
    my $sqlx  = " order by start asc";
    $sqlx    .= " limit 100;";

    # for capital
    my $fromc_cap .= " from capital c join last l on c.x=l.x and c.y=l.y left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $fromc_cap    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    my $condc_cap  = " $cond_aid and f.vid is null and a.x is null "; # not in fakelist neither artifact
    
    # show recommend
    my $union = get_recommend($db, $id, $nart, $nvil, $selc,$rest );
    # print $union;

    # fakenow_show_with_div($db, "filter", "recommend", 5, $selc, $fromc, $cond_fl . $sqlx );
    fakenow_show_with_div_sql($db, "filter", "recommend", 5, $union );
    # shwo fakelist
    fakenow_show_with_div($db, "filter", "fakelist", 1, $selc, $fromc, $cond_fl . $sqlx );

    # shwo intime
    fakenow_show_with_div($db, "filter", "intime", 2, $selc, $fromc, $cond_intime . $sqlx );

    # show artifact villages
    fakenow_show_with_div($db, "filter", "artifact", 3, $selc, $fromc2, $cond_aid . $sqlx );

    # show capitals
    fakenow_show_with_div($db, "filter", "capital", 4, $selc, $fromc_cap, $condc_cap . $sqlx );

    # show players
    my $sqluser = "select uid from last l $cond_aid group by uid order by sum(population) desc;";
    my $sth = do_sql($db, $sqluser);
    my $num = $sth->rows();
    for(my $ix=0;$ix<$num;$ix++){
	my($uid) = $sth->fetchrow_array();
	print "<div id=vt_player_$uid></div>\n";
    }
    $sth->finish();
    #
    # bottom
    #
    print "</div>\n";  # end of right table
    print "</form>\n";
    print "<div style=\"clear: both;\"></div>";

    return 0;
}

sub get_div_title {
    my($db, $name,$value) = @_;

    my %ttitle = (
	"recommend"  => "Recommend",
	"fakelist"  => "Fakelist.",
	"intime"    => "In time.",
	"artifact"  => "Artifacts.",
	"capital"   => "Capitals.",
	"player"    => "$value",
	);
    my $key   = $value;
    my $title = (exists $ttitle{$key})?$ttitle{$key}:"$value";

    if( $name eq "player" ){
	# ($title) = $db->selectrow_array("select user from last where uid = $value limit 1;");
	my $sth = do_sql($db, "select user from last where uid = $value limit 1;");
	($title) = $sth->fetchrow_array();
	$title .= "($value)";
    }
    return $title;
}

# for inline
sub fakenow_show_by_name {
    my($db, $name, $value, $x, $y, $vel, $tsq, $margin, $id, $arrival, $start) = @_;

    my $title = get_div_title($db, $name, $value);
    my $selc  = get_selc($arrival, $x, $y, $vel, $tsq, $margin);
    
    my $dist     = "dist($x,$y,l.x,l.y)";
    my $travel   = "travel($dist, $vel, $tsq)";                     # travel hours
    my $rest     = "TIMESTAMPDIFF(second, \"$start\", \"$arrival\")";    # rest seconds
    my $intime   = "( $rest >= $travel * 3600 )";
    my $intimem  = "( $rest >= ( $travel - $margin ) * 3600)";

    # for general
    my $fromc .= " from last l left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $fromc    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    # for artifact
    my $fromc2 .= " from $t_art a join last l on a.x = l.x and a.y = l.y ";
    $fromc2    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    # aid condition
    my $cond_aid     = " where (l.aid in ($tg_aidlist)) ";
    # for fakelist
    my $cond_fl      = " $cond_aid and ( f.fs = $id and f.enabled > 0 ) ";
    # for inttime
    my $cond_intime  = " $cond_aid and ( $intimem ) ";

    # other clauses
    my $sqlx  = " order by start asc";
    $sqlx    .= " limit 100;";

    #
    # for capital
    #
    my $fromc_cap .= " from capital c join last l on c.x=l.x and c.y=l.y left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $fromc_cap    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    my $condc_cap  = " $cond_aid and f.vid is null and a.x is null "; # not in fakelist neither artifact
    #
    
    if( $name eq "player"){
	my $cond = " $cond_aid and (l.uid = $value) ";
	# my $cond = " $cond_intime and (l.uid = $value) ";
	fakenow_show($db, $name,  $value , 100+$value, $selc, $fromc, $cond . $sqlx );
    } elsif ( $value eq "recommend" ){
	my $nart = 5;
	my $nvil = 3;
	my $sql = get_recommend($db, $id, $nart,$nvil, $selc, $rest);
	fakenow_show($db, $name,  $value , 5, $sql, "", "");
    } elsif ( $value eq "fakelist" ){
	# print "DBG: $selc $fromc $cond_fl $sqlx\n";
	fakenow_show($db, $name,  $value , 1, $selc, $fromc, $cond_fl . $sqlx );
    } elsif ( $value eq "intime" ){
	fakenow_show($db, $name, $value , 2, $selc, $fromc, $cond_intime . $sqlx );
    } elsif ( $value eq "artifact" ){
	fakenow_show($db, "filter", "artifact", 3, $selc, $fromc2, $cond_aid . $sqlx );
    } elsif ( $value eq "capital" ){
	fakenow_show($db, "filter", "capital", 4, $selc, $fromc_cap, $condc_cap . $sqlx );
	# fakenow_show_capital($db, "vt_filter_capital", "<b>$title</b>", 4, $id, $selc);
    }
    print "</bodY></html>\n";
    exit 0;
}

sub fakenow_show_capital {
    my($db, $divid, $title, $ix, $id, $selc) = @_;

    my $sql2 .= " from capital c join last l on c.x=l.x and c.y=l.y left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $sql2    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    my $sql3  = " where l.aid in ($tg_aidlist) ";
    $sql3    .= " and f.vid is null and a.x is null "; # not in fakelist neither artifact
    $sql3    .= " order by start asc";
    # $sql3 .= " limit 20;";

    return fakenow_show( $db, $divid, $title, $ix, $selc, $sql2, $sql3 );
}

sub fakelist_show_capital {
    my($db, $x,$y,$vel,$tsq, $arrival, $id, $title) = @_;

    my $sql1  = "select df(date_sub(\'$arrival\', interval round(travel(dist($x,$y,l.x,l.y), $vel, $tsq) * 3600,0) second )) start, ";
    $sql1 .= " round(travel(dist($x,$y,l.x,l.y), $vel, $tsq),2) duration, round(dist($x,$y,l.x,l.y),2) dist, gridlink(l.x,l.y) grid, ";
    $sql1 .= " usera(l.uid,l.user) player, l.village, l.population pop, ";
    $sql1 .= " iscapitals(l.x,l.y) cap, a.name art, silverg(l.uid) silver, ";

    my $sql2  = " concat('<input type=checkbox name=village value=', l.vid, '>' ) chk ";
    $sql2    .= " from capital c join last l on c.x=l.x and c.y=l.y left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $sql2    .= "   left outer join $fakevil f on f.vid = l.vid and f.fs = $id ";

    my $sql3  = " where l.aid = 22 ";
    $sql3    .= " and f.vid is null and a.x is null "; # not in fakelist neither artifact
    $sql3 .= " order by duration desc";
    $sql3 .= " limit 20;";

    my $sqlvil = $sql1 . $sql2 . $sql3;
    # print "$sqlvil\n";
    my $sth = do_sql($db, $sqlvil);
    print $title;
    show_data_table($sth);
}


sub show_armlog_form {
    my($db) = @_;

    my $cgi = CGI->new();

    my $inplayer = $cgi->param("player");

    print "<form method=post action=\"/$cpath$prog/armlog\">\n";
    #
    # show player selection
    #
    print "<div>\n";
    print "<b>Fileter:</b> Player:";
    print "  <select name=player>\n";
    print "   <option value=-1>---</option>\n";

    my $selected = "";
    $selected = "selected" if( "latest" eq $inplayer );
    print "   <option value=latest $selected>latest</option>\n";

    my $sth = do_sql($db, "select uid,user from last where aid = 22 group by uid order by user;");
    my $nrows = $sth->rows;
    for(my $ix; $ix<$nrows;$ix++){
	my($uid,$user) = $sth->fetchrow_array();
	$selected = "";
	$selected = "selected" if( $user eq $inplayer );
	print "    <option value=$user $selected>$user</option>\n";
    }
    print "  </select>\n";

    #
    # show id month/day for realday update
    #
    my $msg = "複数ＩＤ更新時は、コンマで区切る";
    print "<b>Change Realdate:</b>  ID: <input type=text name=id>";
    print "Month: <input type=text size=4 name=month>";
    print "Day: <input type=text size=4 name=day>";
    print "($msg)\n";
    print "</div>\n";

    #
    # show url list
    #
    print <<EOT
	<ol>
	<li> url1: <input type=text size=80 name=url1>
        <li> url2: <input type=text size=80 name=url2>
	<li> url3: <input type=text size=80 name=url3>
	<li> url4: <input type=text size=80 name=url4>
	<li> url5: <input type=text size=80 name=url5>
	<li> url6: <input type=text size=80 name=url6>
	</ol>
	
	<input type=submit name=register>
	</form>
EOT
;
}

sub armlog_parse_at {
    my($at) = @_;

    my $at  = encode('utf-8', $at);
    my $own = encode('utf-8', "所有");
    $at =~ s/^\s*\[(\S.*)\]\s*(\S.*)\s*$own\s*(\S.*)\s*$/$1,$2,$3/;
    return ($1,$2,$3);
}

sub armlog_findurl {
    my($db, $table, $url ) = @_;

    my $sth = do_sql($db, "select * from $table where url = \"$url\";");
    my $ret = $sth->rows;
    $sth->finish;
    return $ret;
}

sub show_armlog {
    my($kari) = @_;

    #
    # show_armlog_form
    #
    # print "<h1> Attacker log </h1>\n";

    my $db = open_db();
    my $cgi = CGI->new;
    #
    # Handle URL
    #
    my @urls = ();
    foreach my $no (0..9){
	my $pname = sprintf "url%d", $no+1;
	my $url = $cgi->param( $pname );
	if ( defined($url) && length($url) > 0 ){
	    push @urls, $url;
	}
    }
    # print "DBG: Loading ", join("," , @urls), "\n";
    if ( $#urls >= 0 ){
	foreach my $url (@urls){
	    $url =~ s/\s//g;
	    if( armlog_findurl($db, $atmugi, $url) ){
		print "duplicated: $url<br>\n";
		next; 
	    }
#	    print "DBG: parsing $url\n";
	    my $root = HTML::TreeBuilder->new_from_url($url);
#	    print "DBG: searching $root\n";
	    my $ret = parse_report_root2($root, $url);
	}
    }
    #
    # Handle update realdate
    #
    my $id    = $cgi->param("id");
    my $month = $cgi->param("month");
    my $day   = $cgi->param("day");
    if( defined($id) && defined($month) && defined($day) && $id > 0 && $month > 0 && $month < 13 && $day > 0 && $day < 31 ){
	my $newdate = sprintf "2016-%02d-%02d", $month, $day;
	my $sql = "update $atmugi set realdate = \'$newdate\' where id in ($id);";
	my $sth = do_sql($db, $sql);
	$sth->finish;
    } elsif (defined($id) && defined($day) && $day == -1 ) {
	my $sql = "delete from $atmugi where id in ($id);";
	my $sth = do_sql($db, $sql);
	$sth->finish;
    }
    #
    # show
    # 
    show_armlog_form($db);

    my $player = $cgi->param("player");
    my $sql   = "select id,at,mugi,tribe(tribe) tribe, army, dead, realdate ,logdate, ts, note, url from atmugi ";
    my $order = " order by at, ts desc limit 80;";
    my $format = 0;
    
    if( defined($player) && $player eq "latest" ){
	# latest summary
	$sql = "select at , max(realdate) mrealdate , max(mugi) mmugi from atmugi group by at order by mmugi desc, mrealdate desc ";
	$format = 1;
    } elsif( defined($player) && $player ne "" && $player != -1 ){
	$sql .= " where at like \'%$player%\' " . $order;
    } else {
	$sql .= $order;
    }
    my $sth = do_sql($db, $sql);
    
    #    print "DBG: $sql\n";
    if( $format > 0 ){
	my $num_rows = $sth->rows;
	print "<table class=bstyle>\n";
	my @ths = qw(ally player village realdate mugi);
	print "<tr>";
	foreach my $hh (@ths){ print "<th>$hh</th>\n";}
	print "</tr>";

	for (my $i=0; $i<$num_rows; $i++) {
	    my($at,$realdate,$mugi) = $sth->fetchrow_array();
	    my($ally,$player,$village) = armlog_parse_at($at);

	    print "<tr>";
	    print "<td>$ally</td>";
	    print "<td>$player</td>";
	    print "<td>$village</td>";
	    print "<td>$realdate</td>";
	    print "<td>$mugi</td>";
	    print "</tr>";

	}
	print "</table>\n";
        # show_data_table($sth);
    } else {
	my $num_rows = $sth->rows;

	print "<table class=bstyle>\n";

	my $title_ap = $sth->{NAME};
	pop @$title_ap; # remove url at last
	# show table header
	print "<tr>";

	# foreach my $hh (@$title_ap){ print "<th>$hh</th>\n";}
	$title_ap = [qw(id ally player village mugi tribe army dead realdate logdate ts note)];
	foreach my $hh (@$title_ap){ print "<th>$hh</th>\n";}

	print "</tr>";
	# show table body
	my $eo = "even";
	for (my $i=0; $i<$num_rows; $i++) {
	    my ($id,$at,$mugi,$tribe,$army, $dead, $realdate, $logdate, $ts, $note, $url) = $sth->fetchrow_array;
	    $eo = ($eo ne "even" )?"even":"";

	    my($ally,$player,$village) = armlog_parse_at($at);

	    # my($ally,$rest) = 
	    # my($player,$village) = split(/\s+$own\s+/,$rest);
	    
	    print "<tr class=$eo>";
	    print "<td><a href=\"$url\">$id</a></td>";

	    #print "<td align=\"left\">$at</td>";
	    
	    print "<td>$ally</td>";
	    print "<td>$player</td>";
	    print "<td>$village</td>";

	    print "<td>$mugi</td>";
	    print "<td>$tribe</td>";
	    print "<td>$army</td>";
	    print "<td>$dead</td>";
	    print "<td>", dnormal($realdate), "</td>";
	    print "<td>$logdate</td>";
	    print "<td>", dnormal($ts), "</td>";
	    print "<td>$note</td>";
	    print "</tr>\n";

	}
	print "</table>\n";
	$sth->finish;
    }

    close_db($db);
    
}

sub encrypt_passwd {
    my($pass)=@_;
    my @salt_set = ('a'..'z','A'..'Z','0'..'9','.','/');
    srand;
    my $idx1 = int(rand(63));
    my $idx2 = int(rand(63));
    my $salt = $salt_set[$idx1] . $salt_set[$idx2];
    return crypt($pass, $salt);
}

sub poi1 {

    my $q = new CGI;
    my $pass = $q->param('pass');
    my $encpass = &encrypt_passwd($pass);
    print "Content-type: text/plain\n\n";
    print ${encpass};
    exit;
}

sub show_info {
    my($x,$y,$tsq,$vel, $virgin) = @_;

    my %dep = ();

    my $db = open_db();

    my $cgi = CGI->new();
    ($x,$y) = get_location_by_login($db, $cgi, $g_login, $x, $y);

    print "<form name=loc method=post action=/$script/show>";

    show_form_sel_sub($db, $x, $y, $vel, $tsq);
    show_form_params($db, $x, $y, $vel, $tsq);
    show_form_action($x,$y,$tsq,$vel);

    print "</form>\n";

    register_srcdata($db, $x,$y,$tsq,$vel);
    my $srcid = get_id_srcdata($db, $x,$y,$tsq,$vel);
    $srcid = 1 if (!defined($srcid) || $srcid < 1);

    my $sth = do_sql($db, "select id,sx,sy,dx,dy,dtime,stime,regtime,at,df,note from $sktable;");
    my $num_rows = $sth->rows;

    if ( $num_rows < 0 ){
	print "<p> failed to read data from the table $sktable.</p>\n";
	return -1 ;
    }
    #
    # copy db to hash
    #
    for(my $i=0; $i<$num_rows; $i++){
	my ($id, $sx, $sy, $dx,$dy,$dtime, $stime, $regtime, $at, $df, $note) = $sth->fetchrow_array;
	my $hours = hours(dist($x,$y,$dx,$dy),$vel,$tsq);

#	my $dur       = to_dur($hours);         # DateTime::Duration object
	my $dur       = to_dur_sec($hours);     # Time::Seconds object
#	my $desttime  = to_datetime($dtime);    # Time::Piece object
	my $desttime  = to_time_serial($dtime); # Serial from 1900/1/1 0:0:0
	my $starttime = $desttime - $dur;

	my $waves = 1;
        my $content = [$id,$sx,$sy,$dx,$dy,  $dtime,$stime,$regtime,$dur,$at,  $df,$note, $waves];

	if (!defined($dep{$starttime})){
	    $dep{$starttime} = [];
	} else {
	    # detected same starttime
	    my $oldapp = $dep{$starttime};
	    foreach my $op (@$oldapp){
		if ( cmp_wave($op, $content) ){
		    # matched
		    $op->[12]++;  # incriment num waves
		    last;
		}
	    }
	    next;
	}
	my $ap = $dep{$starttime};
	push @$ap, $content;
    }
    $sth->finish;
    #
    # Path 2 unify the around waves
    #
    my %route;
    my %udep;
    
    foreach my $st (sort keys %dep){
	# $st time serial
	my $app = $dep{$st};
	my $start = datestring($st);

	# show same start time
	my $upp = [];

	foreach my $ap (@$app){
	    my ($id,$sx,$sy,$dx,$dy,$dtime,$stime,$regtime,$dur,$at, $df, $note, $waves) = @$ap;

	    my $rkey = "$sx.$sy.$dx.$dy";

	    if( defined($route{$rkey}) ){
		my $last    = $route{$rkey}->[0];
		my $lastowp = $route{$rkey}->[1];

		if( ($st - $last) <= 60 ){

		    # regidter to udep{$last}
		    #
		    # udep{$st} = [  [id,  [[offset,waves],], ... ], [],  ];
		    # incr_udp{$rkey, $udep{$st}, $ap);
		    push @$lastowp, [$st - $last,$waves];
		    next;
		} # if ($st-$last)
	    } # if defined

	    my $owp = [[0,$waves]];  # offset = 0;
	    $route{$rkey} = [$st,$owp];
	    my $uap = [$id,$owp,$sx,$sy,$dx,$dy,$dtime,$stime,$regtime,$dur,$at, $df, $note, $waves];
	    push @$upp , $uap;
	}
	$udep{$st} = $upp;
    }

    #
    # Path 3 print
    #
    my $now = time();
    
    print "<table class=bstyle>\n";
    print "<tr>";
    print join("", map {"<th>" . $_ . "</th>" } qw( Start Arrive Waves Duration Dest DF AT Note ));
    print "</tr>\n";

    my $eo = "even";
    foreach my $st (sort keys %udep){
	my $app = $udep{$st};
	my $start = datestring($st);
	my $color = ( $st >= $now )?"intime":"outoftime";

	# show same start time
	foreach my $ap (@$app){
	    $eo = ( ($color eq "intime") && ($eo ne "even") )?"even":"";

	    my ($id,$owp,$sx,$sy,$dx,$dy,$dtime,$stime,$regtime,$dur,$at, $df, $note, $waves) = @$ap;

	    my $dserial = to_time_serial($dtime);
	    my $dlist = "<table border=0 bgcolor=white>";

	    my $sumwaves = 0;
	    foreach my $pair (@$owp){
		my($offset,$owaves) = @$pair;
		my $dspot = dnormal(datestring($dserial+$offset));
		$dlist .= "<tr><td bgcolor=white>$dspot"."x$owaves</td></tr>";
		$sumwaves += $owaves;
	    }
	    $dlist .= "</table>";
	    
	    my $sdur = to_sdur($dur);
	    $at = encode('utf-8', $at);
	    $df = encode('utf-8', $df);
	    my $loc = location($dx,$dy);

	    my $nstart = dnormal($start);

	    print "<tr class=\"$eo $color\">";

	    print "<td><a href=\"/$cpath$prog/snip/$id/$srcid\">$nstart</a></td>";
	    #print "<td>$ndtime x $waves </td>";
	    print "<td>$dlist</td>";
	    print "<td>$sumwaves</td>";
	    print "<td>$sdur</td>";
	    print "<td>$loc</td>";
	    print "<td>$df</td>";
	    print "<td>$at</td>";
	    print "<td>$note</td>";

	    print "</tr>\n";

	    if( $virgin ){
		$note = $dlist;
		my $query = "insert into $atinfo (sx,sy,dx,dy,stime,dtime,waves,note) values ($sx,$sy,$dx,$dy,\"$stime\",\"$dtime\",$sumwaves,\"$note\")";
#		print "<td>$query</td>";
		my $sth = do_sql($db, $query);
		$sth->finish;
	    }
	    
	}
    }
    print "</table>\n";
    
    #
    # Old Path 3 show hash %dep
    #
    if ( 0 ){

    my $now = time();
    
    if ( 0 ){
	my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst)
	    = localtime(time());
	$year += 1900;
	$mon += 1;

	my $today = sprintf "%04d-%02d-%02d %02d:%02d:%02d", $year, $mon, $mday, $hour, $min, $sec;
    }

#    print "<table border=1>\n";
    print "<table class=bstyle>\n";
    print "<tr>";
    print join("", map {"<th>" . $_ . "</th>" } qw( Start Arrive Duration Dest DF AT Note ));
    print "</tr>\n";

    my $eo = "even";

    foreach my $st (sort keys %dep){
	
	my $app = $dep{$st};
	my $start = datestring($st);

#	my $color = ( $st >= $now )?"GreenYellow":"LightGray";
	my $color = ( $st >= $now )?"intime":"outoftime";


	# show same start time
	foreach my $ap (@$app){

	    #	    print "<tr bgcolor=$color>";
	    $eo = ( ($color eq "intime") && ($eo ne "even") )?"even":"";
	    print "<tr class=\"$eo $color\">";

	    my ($id,$sx,$sy,$dx,$dy,$dtime,$stime,$regtime,$dur,$at, $df, $note, $waves) = @$ap;
	    my $sdur = to_sdur($dur);
	    $at = encode('utf-8', $at);
	    $df = encode('utf-8', $df);
	    my $loc = location($dx,$dy);

	    my $ndtime = dnormal($dtime); my $nstart = dnormal($stime);
	    print "<td><a href=\"/$cpath$prog/snip/$id/$srcid\">$nstart</a></td>";

	    print "<td>$ndtime x $waves </td>";
	    print "<td>$sdur</td>";
	    print "<td>$loc</td>";
	    print "<td>$df</td>";
	    print "<td>$at</td>";
	    print "<td>$note</td>";

	    if( $virgin ){
		my $query = "insert into $atinfo (sx,sy,dx,dy,stime,dtime,waves,note) values ($sx,$sy,$dx,$dy,\"$stime\",\"$dtime\",$waves,\"$note\")";
#		print "<td>$query</td>";
		my $sth = do_sql($db, $query);
		$sth->finish;
	    }
	    
	    print "</tr>\n";
	}
    }
    print "</table>\n";

    }
    #    show_tables($db);

    show_skana($db);
    show_skhist($db);
    show_extensions($db);
    
    close_db($db);
}

sub do_ext {
    my($db,$pp) = @_;

    my($id,$name,$q) = @$pp;

    my $sth = do_sql($db,$q);

    print "<h3>($id) $name</h3>\n";
    show_data_table($sth);
}

sub show_extensions {
    my($db) = @_;

    my $ext = "extensions";

    my $sth = do_sql($db, "select id, name, query from $ext order by id;");
    my $num = $sth->rows;
    for(my $ix=0;$ix<$num;$ix++){
	my @pa = $sth->fetchrow_array();
	do_ext($db, \@pa);
    }
    $sth->finish;

    return 0;
}

sub show_skana {
    my($db) = @_;
    
#    my $query = "select l.alliance, l.user, count(distinct l.vid) nvillage, count(sk.id) nwaves from sk join last l on sk.dx = l.x and sk.dy = l.y group by l.alliance,l.user, l.village with rollup;";
    my $query = "select l.alliance, l.user, l.village, count(sk.id) nwaves from sk join last l on sk.dx = l.x and sk.dy = l.y group by l.alliance,l.user, l.village with rollup;";

#    my @titles = qw(Alliance Player #villages #waves );
#    show_data_table(do_sql($db, $query), \@titles );
    show_data_table( do_sql($db, $query) );
}

sub to_datetime {
    my($dtime) = @_;

#    print "DBG:dtime=$dtime\n";
#    return Time::Piece->strptime($dtime, '%Y-%m-%d %H:%M:%S');
    return Time::Piece->strptime($dtime, '%Y-%m-%d %H:%M:%S');
}

use POSIX qw(floor);

sub to_dur {
    my ($fhours) = @_;

    # day
    my $idd = floor($fhours / 24.0);
    my $fhh = $fhours - $idd *24.0;
    # hour
    my $ihh = floor($fhh);
    my $fmm = ($fhh - $ihh) * 60.0;
    my $imm = floor($fmm);
    my $fss = ($fmm - $imm) * 60.0;
    my $iss = floor($fss);

    #    my $dur = DateTime::Duration->new(days => $idd, hours => $ihh, minutes => $imm, seconds => $iss);
    my $dur = "DateTime can not be used.";
    return $dur;
}

sub to_dur_sec {
    my ($fhours) = @_;

    # day

#    my $dur = Time::Seconds->new(floor($fhours * 3600));
    my $dur = int($fhours * 3600);
    return $dur;
}

sub do_init {
    my $db = open_db();
    do_sql($db, "create table $sktable (id serial, sx int, sy int, dx int, dy int, dtime datetime, stime datetime, regtime datetime, at varchar(128), df varchar(128), note varchar(128));");

    do_sql($db, "create table $skhist (id serial, cnt int, loadat timestamp, note varchar(256) );");

    do_sql($db, "create table $comment_table (id serial, who varchar(64), comment text, note varchar(256));");

    do_sql($db, "create table $atinfo (id serial, sx int, sy int, dx int, dy int, stime datetime, dtime datetime, waves int, note varchar(256), primary key (sx,sy,dx,dy,stime));");

    my $sth = do_sql($db, "create table $atmugi (id serial, ts timestamp, logdate varchar(64), at varchar(128), army varchar(128), dead varchar(128), note varchar(256));");

    $sth->finish;
    close_db($db);
}

sub do_drop {
    my $db = open_db();

    do_sql($db, "drop table $sktable;");
    do_sql($db, "drop table $skhist;");
    do_sql($db, "drop table $comment_table;");
    do_sql($db, "drop table $atinfo;");
    do_sql($db, "drop table $atmugi;");

    close_db($db);
}

sub load_narusa {
    my($nexturl) = @_;
    
    my $lp;

    my $cont = 1;  # first but last
    
    while( defined($nexturl)){
	my $html = get($nexturl);

	($lp, $nexturl) = do_parse_html($html);
	insert_data($lp, $cont);
	$cont = 2; # second but last
	#    show_daeta($lp);
    }
    $cont = 3;
    insert_data([], $cont); # register history
}

sub inline_ally {
    # inline ajax
    my($aid) = @_;

    print "Content-type:text/html; charset=utf-8\n\n";

    if($aid < 0){
	print "\n"; # null
	return;
    }
    my $db = open_db();

    my $sth = do_sql($db, "select uid, user from x_world where aid = $aid group by uid order by user;");
    my $num = $sth->rows;
    for(my $i=0;$i<$num;$i++){
	my ($uid,$user) = $sth->fetchrow_array;
	print "<option value=$uid>$user</option>\n";
    }
    $sth->finish;
    
    close_db($db);
}


sub inline_player {
    # inline ajax
    my($uid) = @_;

    print "Content-type:text/html; charset=utf-8\n\n";

    if($uid < 0){
	print "\n"; # null
	return;
    }
    my $db = open_db();

    my $sth = do_sql($db, "select vid, village from x_world where uid = $uid order by population desc;");
    my $num = $sth->rows;
    for(my $i=0;$i<$num;$i++){
	my ($vid,$village) = $sth->fetchrow_array;
	print "<option value=$vid>$village</option>\n";
    }
    $sth->finish;
    
    close_db($db);
}

sub inline_village {
    # inline ajax
    my($vid) = @_;

    print "Content-type:text/plain; charset=utf-8\n\n";

    if($vid < 0){
	print "0,0\n"; # zero
	return;
    }

    my $db = open_db();

    my $sth = do_sql($db, "select x, y from x_world where vid = $vid;");
    my $num = $sth->rows;
    for(my $i=0;$i<$num;$i++){
	my ($x,$y) = $sth->fetchrow_array;
	print "$x,$y\n";
    }
    $sth->finish;
    
    close_db($db);
}

sub get_location {
    my($cgi) = @_;

    my $x   = $cgi->param("x");
    my $y   = $cgi->param("y");
    my $vel = $cgi->param("vel");
    my $tsq = $cgi->param("tsq");

    return ($x,$y,$vel,$tsq);
}

sub get_filter_param {
    my($cgi) = @_;

    my $margin  = $cgi->param("margin");
    my $id      = $cgi->param("id");
    my $arrival = $cgi->param("arrival");
    my $start   = $cgi->param("start");

    return ($margin,$id,$arrival, $start);
}

sub get_selc {
    my($arrival, $x, $y, $vel, $tsq, $margin, $start) = @_;

    my $dist     = "dist($x,$y,l.x,l.y)";
    my $travel   = "travel($dist, $vel, $tsq)";                     # travel hours
    my $rest     = "TIMESTAMPDIFF(second, \"$start\", \"$arrival\")";    # rest seconds
    
    my $intimem  = "( $rest >= ( $travel - $margin ) * 3600)";
    my $intime   = "( $rest >= $travel * 3600 )";
    
    my $selc  = " select df(date_sub(\'$arrival\', interval round($travel * 3600,0) second )) start, ";
    $selc    .= "   round($travel,2) duration, round($dist,2) dist, gridlink(l.x,l.y) grid, ";
    $selc    .= "   usera(l.uid,l.user) player, l.village,l.population pop,";
    $selc    .= "   iscapitals(l.x,l.y) cap, a.name art, silverg(l.uid) silver, ";
    $selc    .= "   f.reserved, f.fired, case when f.enabled > 0 then 'Y' else '' end FL, ";
    $selc    .= "   concat('<input type=checkbox name=village value=', l.vid, '>' ) chk,  ";
    $selc    .= "   case when $intime then '' else 'Late' end late , ";
    $selc    .= "   df(date_add(now(), interval round($travel * 3600,0) second)) arrive ";

    return $selc;
}

sub inline_filter_filter {
    # inline ajax
    my($db, $cgi, $name, $value) = @_;

    print "Content-type:text/html; charset=utf-8\n\n";

    my($x,$y,$vel,$tsq)      = get_location($cgi);
    my($margin,$id,$arrival, $start) = get_filter_param($cgi);

    fakenow_show_by_name($db, $name, $value, $x,$y,$vel,$tsq,$margin,$id,$arrival, $start);
}
#
# report_table
# id serial, updated timestamp, datetime, uid, user, army, from, to, note
# 
#
my %report_tags = (
    "件名："  => "title",
    "送信"    => "datetime",
    "攻撃者"  => "attacker",
    "防御者"  => "defender",
    "所有"    => "owner",
    "兵士"    => "arm",
    "死傷"    => "dead",
);

sub parse_report_file {
    my($filename) = @_;

    print "Parsing $filename\n";
    my $root = HTML::TreeBuilder->new_from_file($filename);
#    $root->dump();
    return parse_report_root($root);
}
sub parse_report_file2 {
    my($filename) = @_;

    print "Parsing $filename\n";
    my $root = HTML::TreeBuilder->new_from_file($filename);
#    $root->dump();
    return parse_report_root2($root, $filename);
}

#
# parse by structures
#
sub parse_report_root2 {
    my($root, $url) = @_;

    foreach my $m (keys %report_tags ){
	my $em = encode('utf-8', $m);
	$report_tags{$em} = $report_tags{$m};
    }

    my $db = open_db();
    my $body = $root->find("body");
    my @rows = $body->look_down(_tag => "tr");

    my $ix = -1;
    my @data = ();
    my $tribe = 0;

    foreach my $row (@rows){
	my @cols = $row->look_down(_tag => "td");
	my $head = shift @cols;
	my $text = $head->as_text;

	if(exists $report_tags{$text}){
	    my $mark = $report_tags{$text};
	    my $ncols = $#cols;
	    next if ( ($mark eq "dead" ) && $ncols <= 0 );

	    if( $mark eq "title" ){
		$ix++;
		$data[$ix] = {};
	    }
	    my $hp = $data[$ix];

	    # skip defender info
	    next if ( ($mark eq "arm") && (exists $hp->{"arm"}) );
	    next if ( ($mark eq "dead") && (exists $hp->{"dead"}) );
	    
	    my $rd = join(",", map {$_->as_text} @cols );
	    $hp->{$mark} = $rd;
	    # print "DBG:", $mark, "---$ncols---", $rd, "ix=", $ix, "\n";
	} elsif ( $ix >= 0 ){
	    # blank line
#	    print "DBG: found blank line\n";

	    my $img   = $row->find("img");
	    next if ( !defined($img) );

#	    print "DBG: found img tag\n";
	    
	    my $aunit = $img->attr("title");
	    next if ( !defined($aunit) );

#	    print "DBG: found title attr = $aunit\n";

#	    print "DBG: title=$aunit\n";
	    my %tribes = (
		"Legionnaire" => 1, # roman
		"Maceman" => 2, # tuton
		"Phalanx" => 3, # gaul
		);

	    my $hp = $data[$ix];
	    if ( exists $tribes{$aunit} && !defined($hp->{"arm"}) ){
		$tribe = $tribes{$aunit};
		# print "tribe = $tribe\n";
		$hp->{"tribe"} = $tribe;
	    }
	}
	
    }
    foreach my $no (0..$ix){
	my $hp = $data[$no];
	my $title    = $hp->{"title"};
	my $datetime = $hp->{"datetime"};
	my $attacker = $hp->{"attacker"};
	my $arm      = $hp->{"arm"};
	my $dead     = $hp->{"dead"};
	my $tribe    = $hp->{"tribe"};

	$datetime =~ s/report.*$//;
	my @arms   = split(/,/, $arm);
	my @deads  = split(/,/, $dead);

	my $mugi = 0;
	$tribe = 0 if ( !defined($tribe) );
	
	if( $tribe > 0 ){
	    my $mup = $mugiunit{$tribe};
	    my @mua = @$mup;
	    
	    foreach my $aa (@arms){
		my $dd = shift @deads;
		my $uu = shift @mua;
		my $survive = $aa - $dd;
		$mugi += ($survive * $uu);
#		print "DBG: -$aa,$dd,$survive,$uu\n";
	    }
	}
	
	my $sql = "insert into $atmugi (logdate,at, army, dead, note, tribe, mugi, url) ";
	$sql .= " values ( \"$datetime\", \"$attacker\", \"$arm\", \"$dead\", \"$title\", $tribe, $mugi, \'$url\' );";
#	print $sql,"\n";
	my $sth = do_sql($db, $sql);
        $sth->finish;
    }
    close_db($db);
    return 0;
}


sub parse_report_root {
    my($root) = @_;

    my $db = open_db();
    foreach my $m (keys %report_tags ){
	my $em = encode('utf-8', $m);
	$report_tags{$em} = $report_tags{$m};
    }

    #my $head = $root->look_down(_tag => "table", class => "newTable");
    #my $day  = $head->look_down(_tag => "td", class => "do_lewej", colspan => 2); # date/time

    my @heads = $root->look_down(_tag => "table", class => "newTable");

    my @days = ();
    foreach my $hh (@heads){
	my $day  = $hh->look_down(_tag => "td", class => "do_lewej", colspan => 2); # date/time

	if(defined($day)){
	    my $dayp = $day->as_text;
	    $dayp =~ s/report.*$//;
	    # print "DBG: $dayp\n";
	    push @days, $day;
	}

    }
    my @tables = $root->look_down(_tag => "table", class => "wojska_new");

    foreach my $tt (@tables){
	# print "DBG: new table\n";
	my $attacker = 0; # per <table>
	my @trs = $tt->find("tr");

	my $times  = "";
	my $atname = "";
	my $atarm  = "";
	my $atdead = "";

	foreach my $tr (@trs){
	    my $cname  = "new_green do_lewej";
	    my $role   = "role";
	    my $row    = []; my $nrow = 0;

	    my $arole  = $tr->look_down(_tag => "div", class => "role");
	    my $atitle = $tr->look_down(_tag => "td", class => $cname);

	    my @tds = $tr->look_down(_tag => "td", class => qr/jednostki new|pusta new/);
	    foreach my $td (@tds){
		my $txt = $td->as_text;
		if(length($txt)>0) {
		    push @$row, $txt;
		    $nrow++;
		}
	    }
	    my $prole = "";
	    my $senc = encode("utf-8", "攻撃者");
	    if( defined( $arole ) ){
		$prole = $arole->as_text;
		# my @cmp = unpack("C*", $senc);
		# my @doc = unpack("C*", $prole);

		if( $prole eq $senc ){
		    $attacker = 1;
		    $atname = $atitle->as_text;
		}
	    } # if defined arole

	    if( $nrow > 0 ){
		my $mode = $report_tags{$prole};
		my $ptitle = "";
		my $arm    = join(" ", @$row);

		if( defined($atitle) ){ $ptitle = encode("utf-8", $atitle->as_text);}

		my $rowtitle = "row";
		
		if( $attacker == 1 ){
		    $atarm = $arm;
		    $rowtitle = "attacker";
		    $attacker = 2;
		    my $today = shift @days;
		    $times = $today->as_text;
		    $times =~ s/report.*$//;
		    
		} elsif ( $attacker == 2 ){
		    $rowtitle = "dead attacker";
		    $atdead   = $arm;
		    $attacker = 0;
		}
		# print
		if($attacker == 2){
		    print $times, "\n";
		    print $atname, "\n";
		}
		print $rowtitle, ":", join(" ", @$row),"\n";
	    } # if nrow > 0
	} # foreach tr
	$times =~ s/^\s+//;
	next if ($times eq "");

	my $sql = "insert into $atmugi (logdate,at, army, dead) ";
	$sql .= " values (\"$times\", \"$atname\", \"$atarm\", \"$atdead\");";
	print $sql,"\n";
	my $sth = do_sql($db, $sql);
        $sth->finish;
			 
    } # foreach table
    close_db($db);
}

sub do_snip {
    my ($skid,$srcid, $params) = @_;

    my $db = open_db();

    #
    # read sktable
    #
    my $sth = do_sql($db, "select id,sx,sy,dx,dy,dtime,stime,regtime,at,df,note from $sktable where id = $skid;");

    my $num_rows = $sth->rows;
    if ($num_rows < 1){
	print "can not find lamp data table.(skid=$skid,srcid=$srcid)\n";
	return 0;
    }
    my ($id, $sx, $sy, $dx,$dy,$dtime, $stime, $regtime, $at, $df, $note) = $sth->fetchrow_array;
    #
    # read srctable
    #
    my($newsrcid, $x, $y, $vel, $tsq);
    if( $srcid eq "last" ){
	# read from cgi parameters
	$newsrcid = -1;
	($x, $y, $vel, $tsq) = @$params;
    } else {
	my $sth = do_sql($db, "select id,x,y,vel,tsq from $srctable where id = $srcid;");
	my $num_rows = $sth->rows;
	if ($num_rows < 1){
	    print "can not find source data.";
	    return 0;
	}
	($newsrcid, $x, $y, $vel, $tsq) = $sth->fetchrow_array();
    }
    #
    # show parmeters
#    print "<table><tr><td>x=$x</td><td>y=$y</td><td>vel=$vel</td><td>tsq=$tsq</td>\n";
    #
    show_snip_form($skid, $x, $y, $vel, $tsq);
    my $tsqnote = "TSQ: 傭兵ブーツ+2.5　戦士ブーツ+5.0　アルコンブーツ+7.5";
    print "<p>$tsqnote</p>";
    
    # show start times
    my @vels = (3,4,5,6,7,9,10,13,14,16,17,19);
    my @arms = qw( Catapa Ram/Senator/Chief Pre/Chieftain Legio/Sword/Ax Imperi/Pharanx/Bunbun/Spearman Skout/Knight Caesarius/Paladin Headuan Impera Legati/Druid Pathfa Thunder);

    print "<table class=bstyle>\n";

    print join("",map {"<th>".$_."</th>"} qw(Vel Army Start Arrival Duration Destination DF AT Note));

    my $ix = 0;

#    foreach my $vel ( sort {$b <=> $a } @vels){
    foreach my $vel (@vels){
	my $arm   = $arms[$ix++];
	my $hours = hours(dist($x,$y,$dx,$dy),$vel,$tsq);

	my $dur     = to_dur_sec($hours);     # Time::Seconds object
	my $dserial = to_time_serial($dtime);
	my $sserial = $dserial - $dur;
	my $now = time();

	my $color = ( $sserial >= $now )?"GreenYellow":"LightGray";

	my $stime = datestring($sserial);

	my $sdur = to_sdur($dur);
	my $loc  = location($dx,$dy);

	print "<tr bgcolor=$color>";

	print "<td>$vel</td>";
   	print "<td>$arm</td>";

	    print "<td><a href=\"/$cpath$prog/snip/$id/$srcid\">$stime</a></td>";

	    print "<td>$dtime </td>";
	    print "<td>$sdur</td>";
	    print "<td>$loc</td>";
	    print "<td>$df</td>";
	    print "<td>$at</td>";
	    print "<td>$note</td>";

	    print "</tr>\n";
    }

    print "<table class=bsylte>\n";
	
    $sth->finish;
    
    close_db($db);
    
}

sub exec_fakelist {
    my($db, $x,$y,$vel,$tsq) = @_;

    init_fakenow($db);

    my $cgi = CGI->new();
    my ($exec,$cid,$cfid,$crev,$carrival) = fakelist_get_cgi_param($cgi);

    my $ret = 0;
    
    if( defined($exec) ){
	# print "exec ";
	if( $exec eq $msg{set_arrival} ){
	    # set arrival
	    # print "-- set arrival -- $cid, $cfid, $crev, $carrival ";

	    my $ret = $db->do("update $fakenow set arrival = \"$carrival\" where id=$cid;");
	} elsif( $exec eq $msg{set_player} ){
	    # set player
	    my @players = $cgi->param("player");
	    my $playlist = join(",", @players);
	    # print "-- set player -- $cid, $cfid, $crev, $carrival ";
	    # print "... $playlist ";
	    $db->do("delete from $fakeplayer where fs = $cid;");
	    foreach my $uid (@players){
		# print "inserting ($cid,$uid) ";
		my $num = $db->do("insert into $fakeplayer (fs,uid) values ($cid, $uid);");
		# print "DBG: $num inserted into $fakeplayer\n";
	    }
	} elsif( $exec eq $msg{set_village} ){
	    # set village but no rev up.
	    my @vils = $cgi->param("village");
	    # print "exec -- set vil -- $cid, $cfid, $crev, $carrival -- ", join(",",@vils), "\n";
	    $db->do("delete from $fakevil where fs = $cid;");
	    foreach my $vid (@vils){
		my $sql = "insert into $fakevil (fs,vid) values ( $cid, $vid );";
		# print "-- $cid, $vid\n";
		$db->do($sql);
	    }
	} elsif( $exec eq $msg{fix} ){
	    # set fix mark
	    # print "-- fix -- $cid, $cfid, $crev, $carrival ";
	    $ret = $db->do("update $fakenow set fixed = 1 where id = $cid;");
	    # print "DBG: fix = $ret , on id = $cid \n";
	} elsif( $exec eq $msg{save} ){
	    # rev up
	    # print "-- save -- $cid, $cfid, $crev, $carrival ";
	    # insert new fake rev
	    my $newrev = $crev + 1;
	    my $ret = $db->do("insert into $fakenow (fid, rev, arrival) values ($cfid,$newrev, \"$carrival\");");
	    my $sth = do_sql($db, "select id from $fakenow where fid = $cfid and rev = $newrev;");

	    # get new fake serial(fs)
	    my ($newfs) = $sth->fetchrow_array();
	    $sth->finish;

	    # copy from previous revision
	    my $ret1 = $db->do("insert into $fakeplayer (fs,uid) select $newfs, uid from $fakeplayer where fs = $cid;" );
	    my $ret2 = $db->do("insert into $fakevil    (fs,vid) select $newfs, vid from $fakevil    where fs = $cid;" );
	    # print "DBG: newfs=$newfs, oldfs=$cid crev = $crev newcrev = $newrev ($ret1,$ret2)\n";

	} elsif( $exec eq $msg{new} ){
	    # new fakeset
	    my $nextfid = $cfid + 1;
	    my $ret = $db->do("insert into $fakenow (fid,rev,arrival) values ($nextfid, 0, \"$carrival\");");
	} elsif( $exec eq $msg{list} ){
	    #
	    # show fakelist
	    #
	    # show_head("Fakelist for forum");

	    # my $t_art     = "art";
	    # my $t_capital = "capital";
	    print "<table border=0>";
	    #
	    # ff fakevil
	    #
	    if(1){
		# selected
		my $title = "selected";
		print "<tr><td>$title</td></tr>";

		my $sql = "select bbgrid(l.x,l.y) grid, bbuser(l.uid) user, case when c.x is null then '' else 'cap' end cap, a.name aname";

		$sql .= " from $fakevil f join last l  on f.vid = l.vid and f.fs = $cid ";
		$sql .= " left outer join $t_art a     on a.x = l.x and a.y = l.y ";
		$sql .= " left outer join $t_capital c on c.x = l.x and c.y = l.y ";

		$sql .= " where l.aid = 22 ";
		$sql .= " order by l.y desc;";
	    
		my $sth = do_sql($db, $sql );
		my $num_rows = $sth->rows();
		for(my $ix=0;$ix<$num_rows;$ix++){
		    my($grid, $user,$cap,$aname) = $sth->fetchrow_array();
		    # if ($cap eq "cap" ){ $cap = $msg{"capital"};}
		    print "<tr><td>$grid</td><td>$user</td><td>$cap</td><td>$aname</td></tr>";
		}
	    }
	    #
	    # ff artifacts
	    #
	    my $sql = "select bbgrid(a.x,a.y) grid, bbuser(l.uid) player, a.name, case when c.x is null then '' else 'cap' end cap from $t_art a join last l on a.x=l.x and a.y=l.y left outer join $t_capital c on c.x=l.x and c.y=l.y where l.aid = 22 order by l.uid ;";
	    my $sth = do_sql($db, $sql );
	    my $num_rows = $sth->rows();

	    my $title = $msg{"artifact"};
	    print "<tr><td>$title</td></tr>";

	    for(my $ix=0;$ix<$num_rows;$ix++){
		my($grid, $player, $aname, $cap) = $sth->fetchrow_array();
		# if ($cap eq "cap" ){ $cap = $msg{"capital"};}
		print "<tr><td>$grid</td><td>$player</td><td>$cap</td><td>$aname</td></tr>";
	    }
	    #
	    # ff players
	    #
	    my $title = "Players";
	    print "<tr><td>$title</td></tr>";

	    my $sth = do_sql($db, "select f.uid from $fakeplayer f where fs = $cid;");
	    my $num_rows = $sth->rows();
	    for(my $ix=0;$ix<$num_rows;$ix++){
		my($uid) = $sth->fetchrow_array();
		
		print "<tr><th>--- \[player\]$uid\[/player\] ---</td><td></td></tr>";
		my $st2  = do_sql($db, "select bbgrid(l.x,l.y) grid, a.name artname, case when c.x is null then '' else 'cap' end cap from last l left outer join $t_capital c on c.x=l.x and c.y=l.y left outer join $t_art a on a.x = l.x and a.y = l.y where l.uid = $uid order by l.population desc;");
		my $num2 = $st2->rows();
		for(my $ix2=0;$ix2<$num2;$ix2++){
		    my($grid, $aname, $cap) = $st2->fetchrow_array();
		    # if ($cap eq "cap" ){ $cap = $msg{"capital"};}
		    print "<tr><td>$grid</td><td>$cap</td><td>$aname</td></tr>";
		}
	    }
	    #
	    # ff Caitals
	    #
	    if(0){
		my $title = $msg{"capital"};
		print "<tr><td>$title</td></tr>";

		my $sql = "select bbgrid(l.x,l.y) grid, bbuser(l.uid) user, l.user player";
		$sql .= " from $t_capital c join last l on c.x   = l.x and c.y = l.y ";
		$sql .= " left outer join $fakeplayer f on f.uid = l.uid ";
		$sql .= " left outer join $t_art a      on a.x   = l.x and a.y = l.y ";
		$sql .= " where f.uid is null and a.x is null and l.aid in ($tg_aidlist) ";
#		$sql .= "   and l.uid in (select uid from last where aid = 22 group by uid order by sum(population) desc limit 20) ";
		$sql .= " order by l.population desc ;";
	    
		my $sth = do_sql($db, $sql );
		my $num_rows = $sth->rows();
		for(my $ix=0;$ix<$num_rows;$ix++){
		    my($grid, $user, $player) = $sth->fetchrow_array();
		    print "<tr><td>$grid</td><td>$user</td><td>$player</td></tr>";
		}
	    }
	    #
	    # ff footer
	    #
	    print "</table>\n";
	    show_tail();
	    exit 0;
	}
    }

    return show_fakelist($db,$x,$y,$vel,$tsq);
}

sub fakelist_show_hidden {
    my($id,$fid,$rev) = @_;
    
    print "<input type=hidden name=id value=$id>\n";
    print "<input type=hidden name=fid value=$fid>\n";
    print "<input type=hidden name=rev value=$rev>\n";
}

sub fakelist_get_cgi_param {
    my ($cgi ) = @_;
    
    my $exec     = $cgi->param("exec");
    my $cid      = $cgi->param("id");
    my $cfid     = $cgi->param("fid");
    my $crev     = $cgi->param("rev");
    my $carrival = $cgi->param("arrival");

    return ($exec,$cid,$cfid,$crev,$carrival);
}

    
sub show_fakelist {
    my($db, $x,$y,$vel,$tsq) = @_;

    init_fakenow($db);

    print "<form method=post action=\"/$script/fakelist/exec\">\n";

    my $cgi = CGI->new();
    my ($exec,$cid,$cfid,$crev,$carrival) = fakelist_get_cgi_param($cgi);

    # my $sql = "select id, fid, rev, arrival, fixed from $fakenow order by id desc limit 1;";
    my $sql = "select id, fid, rev, arrival, fixed from $fakenow where fid = (select max(fid) from fakenow limit 1) order by rev desc limit 1;";
    my ($id, $fid, $rev, $arrival, $fixed) = $db->selectrow_array($sql);
    fakelist_show_hidden($id,$fid,$rev);

    if( !defined($id) ){
	$id = 0; $fid = 0; $rev = 0;
	$arrival = datestring(time() + 3600*24); # 1 day later as default
    }
    
    # Top div
    print "<div>";

    print "<table border=0>";
    print "<tr>";

    print "<td>Flight $fid</td>";
    print "<td>Rev.$rev (SN=$id)</td>";

    print "<td>Arrival</td><td><input type=text name=arrival value=\"$arrival\"></td>";
    print "<td><input type=submit name=exec value=\"$msg{set_arrival}\"></td>";

    $cgi = CGI->new();
    ($x,$y) = get_location_by_login($db, $cgi, $g_login, $x, $y);

    print "<td>X</td><td><input type=text size=5 name=x value=$x></td>";
    print "<td>Y</td><td><input type=text size=5 name=y value=$y></td>";
    print "<td>VEL</td><td><input type=text size=5 name=vel value=$vel></td>";
    print "<td>TSQ</td><td><input type=text size=5 name=tsq value=$tsq></td>";
    print "<td><input type=submit name=exec value=\"$msg{set_grid}\"></td>";

    print "</tr>";
    print "</table>";

    print "<p>";
    print "<input type=submit name=exec value=\"$msg{new}\">";
    print "<input type=submit name=exec value=\"$msg{save}\">";
    print "<input type=submit name=exec value=\"$msg{fix}\">";
    print "<input type=submit name=exec value=\"$msg{list}\">";
    print "</p>";
    print "</div>";
    #
    # left div
    print "<div style=\"float:left;vertical-align:top;\">";
    # button
    print "<p><input type=submit name=exec value=\"$msg{set_player}\"></p>";
    # players list
    # username, checkbox
    $sql = "select l.user, concat('<input type=checkbox name=player value=', l.uid, case p.enabled when 1 then ' checked' else '' end, '>') chk from last l left outer join $fakeplayer p on l.uid = p.uid and p.fs = $id where l.aid = 22 group by l.uid order by sum(l.population) desc;";
    my $sth = do_sql($db, $sql);
    show_data_table($sth);
    print "</div>\n";

    print "<div style=\"float:left;width=20px;\"></div>"; # SPACER

    # right div
    print "<div style=\"float:left;vertical-align:top;\">";
    print "<p><input type=submit name=exec value=\"$msg{set_village}\"></p>";

    # show villages : conditions:  uid in $fakeplayer  or  vid in $fakevil
    print "<div>";

    print "selected.";

    my $sql1  = "select date_sub(\'$arrival\', interval round(travel(dist($x,$y,l.x,l.y), $vel, $tsq) * 3600,0) second ) start, ";
    $sql1 .= " round(travel(dist($x,$y,l.x,l.y), $vel, $tsq),2) duration, round(dist($x,$y,l.x,l.y),2) dist, gridlink(l.x,l.y) grid, ";
    $sql1 .= " l.user player, l.village,l.population pop, ";
    $sql1 .= " iscapitals(l.x,l.y) cap, case when a.name is null then '' else a.name end art, silverg(l.uid) silver, ";

    my $sql2  = " concat('<input type=checkbox name=village value=', l.vid, case v.enabled when 1 then ' checked' else '' end, '>') chk ";
    $sql2    .= " from last l left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $sql2    .= "   left outer join $fakevil    v on v.vid = l.vid and v.fs = $id ";
    $sql2    .= "   left outer join $fakeplayer u on u.uid = l.uid and u.fs = $id ";

    my $sql3  = " where l.aid in ($tg_aidlist) ";
       $sql3 .= " and ( v.vid is not null )";
       $sql3 .= " group by l.vid ";
       $sql3 .= " order by duration desc ;";

    $sth = do_sql($db, $sql1 . $sql2 . $sql3);

    show_data_table($sth);
    print "</div>";

    print "<hr>";

    # players
    print "<div>";

    my $sql1  = "select date_sub(\'$arrival\', interval round(travel(dist($x,$y,l.x,l.y), $vel, $tsq) * 3600,0) second ) start, ";
    $sql1 .= " round(travel(dist($x,$y,l.x,l.y), $vel, $tsq),2) duration, round(dist($x,$y,l.x,l.y),2) dist, gridlink(l.x,l.y) grid, ";
    $sql1 .= " l.user player, l.village,l.population pop, ";
    $sql1 .= " iscapitals(l.x,l.y) cap, case when a.name is null then '' else a.name end art, silverg(l.uid) silver, ";

    my $sql2  = " concat('<input type=checkbox name=village value=', l.vid, case v.enabled when 1 then ' checked' else '' end, '>') chk ";
    $sql2    .= " from last l left outer join $t_art a on l.x = a.x and l.y = a.y ";
    $sql2    .= "   left outer join $fakevil    v on v.vid = l.vid and v.fs = $id ";
    $sql2    .= "   left outer join $fakeplayer u on u.uid = l.uid and u.fs = $id ";

    my $sql3  = " where l.aid in ($tg_aidlist) ";
       $sql3 .= " and ( (u.uid is not null ) and (v.vid is null) )";
       $sql3 .= " group by l.vid ";
       $sql3 .= " order by duration desc ;";

    $sth = do_sql($db, $sql1 . $sql2 . $sql3);

    print "players.";
    show_data_table($sth);
    print "</div>";

    print "<hr>";

    # show artifact
    print "<div>";

    my $sql1  = "select date_sub(\'$arrival\', interval round(travel(dist($x,$y,l.x,l.y), $vel, $tsq) * 3600,0) second ) start ";

    $sql1 .= ", round(travel(dist($x,$y,l.x,l.y), $vel, $tsq),2) duration, round(dist($x,$y,l.x,l.y),2) dist, gridlink(l.x,l.y) grid ";
    $sql1 .= ", l.user player, l.village,l.population pop ";
    $sql1 .= ", iscapitals(l.x,l.y) cap ";
    $sql1 .= ", a.name art ";
    $sql1 .= ", silverg(l.uid) silver "; # stall was fixed. It was because two silver artifact caused.

    my $sql2a  = ", concat('<input type=checkbox name=village value=', l.vid, case v.enabled when 1 then ' checked ' else '' end, '>' ) chk ";

    my $sql2f  = " from $t_art a join last l on a.x = l.x and a.y = l.y ";
    $sql2f    .= " left outer join $fakevil v on v.vid = l.vid and v.fs = $id ";
    
    my $sql3a  = " where l.aid in ($tg_aidlist) ";
       $sql3a .= " group by l.vid ";
       $sql3a .= " order by duration desc";
    
    $sth = do_sql($db, "$sql1 $sql2a $sql2f $sql3a ;");
    print "Artifacts.";
    show_data_table($sth);

    print "</div>";    # end of artifact
    print "<hr>";

    fakelist_show_capital($db, $x,$y,$vel,$tsq, $arrival, $id, "Captails without artifact not in fakelist.");
    print "</div>\n";  # end of left
    print "</form>\n";

    # bottom
    print "<div style=\"clear: both;\">";
    print "</div>\n";

}

sub art_form {
    print "<form name=art method=post action=\"/$script/artifact\">";

    print "<table border=0>";
    print "<tr>";
    print "<td> x <input type=text size=5 name=x></td>";
    print "<td> y <input type=text size=5 name=y></td>";
    print "<td> name <input type=text name=name></td>";
    print "<td> Level <select name=level>";
    print "<option value=0>Bronz</option>";
    print "<option value=1>Silver</option>";
    print "<option value=2>Unique</option>";
    print "</select></td>";
    print "<td>note <input type=text name=note></td>";
    print "<td><input type=submit name=exec value=add></td>";
    print "</tr>";
    print "</table>";

    print "</form>\n";
}

sub show_art {
    my($db,$cgi) = @_;

    my $ax    = $cgi->param("x");
    my $ay    = $cgi->param("y");
    my $ano   = $cgi->param("no");
    my $level = $cgi->param("level");
    my $name  = $cgi->param("name");
    my $note  = $cgi->param("note");
    my $exec  = $cgi->param("exec");
    my $setid = $cgi->param("set");

    if( $exec eq "add" ){
	# add x,y,name, level
	my $sql = "insert into $t_art (x,y,name,level,note) values ($ax,$ay,\"$name\",$level,\"$note\");";
	$db->do($sql);
    } elsif( $setid > 0 ){
	# set x,y
	my $sql = "update $t_art set x=$ax, y=$ay, no=$ano, note=\"$note\" where id=$setid;";
	$db->do($sql);
    }

    show_head("Artifact");

    # print "DBG: ($ax, $ay) no $ano level $level name $name exec $exec set $setid note $note\n";
    # show form for add
    
    art_form($cgi);

    # show list
    my @labels = qw(id name no grid village user ally cap x y no note set);

    my $sql = "select a.id, a.x, a.y, a.name, a.bronz, a.level, gridlink(a.x,a.y) grid, l.village, l.user, l.alliance, case when c.x is not null then \"capital\" else \"\" end cap, no, note from $t_art a join last l on a.x = l.x and a.y = l.y left outer join capital c on c.x = a.x and c.y = a.y  order by a.name, a.no, a.id;";
    my $sth = do_sql($db,$sql);
    my $num_rows = $sth->rows();

    print "<table class=bstyle>";
    print "<tr>";

    print join("", map { "<th>".$_."</th>" } @labels );
    print "</tr>";
    for(my $ix=0;$ix<$num_rows;$ix++){
	print "<tr>";
	print "<form name=artlist method=post action=\"/$script/artifact\">";

	my($id,$x,$y,$name,$bronz,$level,$grid,$vil, $user,$ally, $cap, $ano, $note) = $sth->fetchrow_array();

	# data
	print "<td>$id</td>";
	print "<td>$name</td>";
	print "<td>$ano</td>";
	print "<td>$grid</td>";
	print "<td>$vil</td>";
	print "<td>$user</td>";
	print "<td>$ally</td>";
	print "<td>$cap</td>";

	# buton
	print "<td><input type=text size=5 name=x value=$x></td>";
	print "<td><input type=text size=5 name=y value=$y></td>";
	print "<td><input type=text size=5 name=no value=$ano></td>";
	print "<td><input type=text name=note value=$note></td>";
	print "<td><input type=submit size=5 name=set value=$id></td>";

	print "</form>\n";
	print "</tr>";
    }
    print "</table>\n";
    # show_tail();
}

#
# travel
#

sub show_form_target {
    my($db, $cgi, $action) = @_;

    my $aid = $cgi->param("aid");
    my $uid = $cgi->param("uid");

    if( $action ){
	print "<form name=target method=post action=$action>\n";
    }

    print "Target: ";
    print "ALLY ID : <input type=text size=5 name=aid value=$aid>";
    print " Player ID: <input type=text size=5 name=uid value=$uid>";
    print "<input type=submit name=exec value=update>";

    if( $action ){
	print "</form>";
    }

    return ($aid,$uid);
}


sub travel_show {
    my($db, $cgi, $x,$y,$tsq,$vel) = @_;
    
    ($x,$y) = get_location_by_login($db, $cgi, $g_login, $x, $y);
    my $action = "/$script/travel";
    #
    # form
    #
    print "<div clas=param>";
    print "<form name=loc method=post action=$action>";
    show_form_sel_sub($db, $x, $y, $vel, $tsq );
    show_form_params($db, $x, $y, $vel, $tsq);
    # show_form_action($x, $y, $tsq, $vel, $action);
    show_form_action($x, $y, $tsq, $vel);
    register_srcdata($db, $x,$y,$tsq,$vel);
    my $srcid = get_id_srcdata($db, $x,$y,$tsq,$vel);
    $srcid = 1 if (!defined($srcid) || $srcid < 1);
    # destination selection
    print "<br>";
    my ($target_aid,$target_uid) = show_form_target($db, $cgi);
    print "c after ALLY_ID will show only capita. Example: 22c";
    print "</form>";
    print "</div>";
    #
    # show alliance div
    #
    my $sth1 = do_sql($db,"select aid, alliance, sum(population) pop from last l group by aid, alliance order by sum(population) desc limit 20;");
    print "<div style=\"float:left;\">";
    show_data_table($sth1);
    print "</div>";
    
    my $cond = "";
    if( defined($target_uid) && $target_uid > 0 )   { 
	# if( $target_uid =~ /^(\d+)\s*[Cc]\s*$/ ){
	if( $target_uid =~ /^(\d+)\s*[Cc]\s*$/ ){
	    $target_uid = substr($target_uid, 0, length($target_uid)-1);
	    # $target_uid = $1;
	    $cond = " where c.x is not nul ";
	    $cond .= " and l.uid in ( $target_uid ) ";
	} else {
	    $cond = " where l.uid in ( $target_uid ) ";
	}
    } elsif( defined($target_aid) && $target_aid > 0 ){
	if( $target_aid =~ /^(\d+)\s*[Cc]\s*$/ ){
	    $target_aid = substr($target_aid, 0, length($target_aid)-1);
	    $cond = " where l.aid in ( $target_aid ) and c.x is not null "; 
	} else {
	    $cond = " where l.aid in ( $target_aid ) ";
	}
    } else {
	$cond = " where l.aid in ($tg_aidlist) and c.x is not null "; 
    }
    
    my $sql = "select round(travel(dist(l.x,l.y,$x,$y),$vel,$tsq),2) hour, \
                 gridlink(l.x,l.y) grid, usera(l.uid,l.user) player, \
                 l.village, l.population, l.uid, l.aid ,\
                 case when c.x is null then '' else 'cap' end cap, \
                 a.name art \
               from last l left outer join $t_capital c on l.x=c.x and l.y = c.y left outer join $t_art a on l.x = a.x and l.y = a.y $cond \
               order by dist(l.x,l.y,$x,$y) asc; ";

    my $sth = do_sql($db, $sql);
    my $num_rows = $sth->rows;

    if ( $num_rows < 0 ){
	print "<p> failed to read data from the table ($target_aid, $target_uid).</p>\n";
	return -1 ;
    }
    print "<div style=\"float:left;\">";
    show_data_table($sth);
    print "</div>";
    print "<div style=\"clear: both;\"";
}

#
# Main
#

#
# create table sk (id serial, sx int, sy int, dx int, dy int, dtime datetime, stime datetime, regtime datetime, note varchar(128));
#
# Load CMD
# 0. truncate sk
# 1. load from kuma
# 2. parse
# 3. insert sk
#
# View CMD
#
# 1. Set parameters
#    x, y, tsq, velocity
#
# 2. show info
#    MY_STARTTIME, dtime, traveltime, link(dx, dy), village, link(user)
#    
#

#
# Auth
#
# Pass 1. Authed -> go
# Pass 2. Not authed -> show_auth_dialog
# Pass 3. From auth_dialog -> go with set-cookie in show_header() or show_auth_dialog()
#
my $lp;

my $info = "";
my $inline = 0;

my($x,$y,$vel, $tsq) = (0,0,3,20);

my $cgi = CGI->new();

if ( $#ARGV < 0 ) {
    # Auth
    auth();

    # CGI mode
    $info = $ENV{"PATH_INFO"};

    # remove heading /
    $info =~ s/^\///;

    $x   = $cgi->param("x");
    $y   = $cgi->param("y");
    $vel = $cgi->param("vel");
    $tsq = $cgi->param("tsq");

    $x = 0    if (!defined($x)); 
    $y = 0    if (!defined($y)); 
    $vel = 3  if (!defined($vel));
    $tsq = 20 if (!defined($tsq));

} else {
    # command line mode
    $info = $ARGV[0];
}

if( $info =~ /show/ || $info eq "" ){
    show_head();
    show_info($x,$y,$tsq,$vel, 0);
} elsif( $info =~ /^atinfo/ ){
    show_head("AT発射履歴");
    show_atinfo();
} elsif( $info =~ /^update_atinfo/ ){
    show_head("AT発射履歴更新");
    print "<h2>update_atinfo: $x $y $vel $tsq</h2>\n";
    show_info($x,$y,$tsq,$vel, 1);
} elsif ( $info =~ /^snip\/(\d+)\/(\d+)/ ){
    my($skid,$srcid) = ($1,$2);
    show_head("差し込み用速度別発射時刻一覧");
    do_snip($skid,$srcid);
    
} elsif ( $info =~ /^snip\/(\d+)\/last/ ){
    my($skid,$srcid) = ($1,"last");
    show_head("差し込み用速度別発射時刻一覧");
    do_snip($skid,$srcid, [$x,$y,$vel,$tsq]);
    
} elsif ( $info =~ /test/ ){
} elsif ( $info =~ /comment/ ){
    show_head();
    do_comment();
} elsif ( $info =~ /reinit/ ){
    show_head();
    do_drop();
    do_init();
} elsif ( $info =~ /init/ ){
    show_head();
    do_init();
} elsif ( $info =~ /load_narusa/ ){
    show_head("データロード");
    load_narusa($kumaurl);
    show_info($x,$y,$tsq,$vel, 1);
} elsif ( $info =~ /insert/ ) {
    # insert from file
    # cmd line only
    my $next;
    show_head();
    ($lp, $next) = do_parse_file($ARGV[1]);
    insert_data($lp);
} elsif ( $info =~ /sk/ ) {
    # show from db
    my $db = open_db();

    show_head("元データダンプ");
    my $sth = do_sql($db, "select count(*) from $sktable;");
    show_data_table($sth);

    $sth = do_sql($db, "select * from $sktable;");
    show_data_table($sth);

    close_db($db);
} elsif ( $info =~ /html/ ) {
    my $html = get($kumaurl);
    my $next;
    show_head();
    ($lp, $next) = do_parse_html($html);
    show_raw_data($lp);
} elsif ( $info =~ /raw/ ) {
    # dump after html
    # cmdline only
    my $next;
    show_head();
    ($lp, $next) = do_parse_file($ARGV[1]);
    show_raw_data($lp);
} elsif ( $info =~ /fakenow\/filter\/filter\/(.*)/ ){
    # misc filter
    my $name = "filter";
    my $value = $1; # recommend, fakelist, intime, capital, artifact
    $inline = 1;
    my $db = open_db();
    inline_filter_filter($db, $cgi, $name,$value);
    close_db($db);
    
} elsif ( $info =~ /fakenow\/filter\/player\/(.*)/ ){
    # player filter
    my $name = "player";
    my $value = $1; # uid
    $inline = 1;

    my $db = open_db();
    inline_filter_filter($db, $cgi, $name, $value);
    close_db($db);
    
} elsif ( $info =~ /ally\/(\d+)/ ){
    # inline ajax
    inline_ally($1);
    $inline = 1;
} elsif ( $info =~ /player\/(\d+)/ ){
    # inline ajax
    inline_player($1);
    $inline = 1;
} elsif ( $info =~ /village\/(\d+)/ ){
    # inline ajax
    inline_village($1);
    $inline = 1;
} elsif ( $info eq "report"){
    # report parser
    parse_report_file($ARGV[1]);
} elsif ( $info eq "report2"){
    # report parser
    parse_report_file2($ARGV[1]);
} elsif ( $info =~ /armlog/ ){
    # parse armlog and register
    show_head("Attacker log");
    show_armlog();
} elsif ( $info =~ /fakenow\/exec/ ){
    # exec fake now
    show_head("Fake now");
    my $db = open_db();
    exec_fakenow($db, $cgi, $x,$y,$vel,$tsq);
    close_db($db);
} elsif ( $info =~ /fakenow/ ){
    # fake now
    show_head("Fake now");
    my $db = open_db();
    show_fakenow($db, $cgi, $x,$y,$vel,$tsq);
    close_db($db);

} elsif ( $info =~ /fakelist\/exec/ ){
    show_head("Fakelist");
    my $db = open_db();
    exec_fakelist($db, $x,$y,$vel,$tsq);
    close_db($db);
} elsif ( $info =~ /fakelist/ ){
    # fake now
    show_head("Fakelist");
    my $db = open_db();
    show_fakelist($db, $x,$y,$vel,$tsq);
    close_db($db);

} elsif ( $info =~ /login/ ){
    # login
    show_auth_dialog();
    exit 0;

} elsif( $info =~ /^artifact/ ){
    my $db = open_db();
    show_art($db,$cgi);
    close_db($db);
} elsif( $info =~ /^travel/ ){
    show_head("Travel calculator");
    my $db = open_db();
    travel_show($db,$cgi, $x, $y, $tsq, $vel);
    close_db($db);

# others

} elsif ( $ENV{"REQUEST_URI"} =~ /$cpath$prog/ ){
    show_head();
    show_info($x,$y,$tsq, $vel,0 );
} elsif ( $info eq "sql" ){
    # execute sql
    my $db = open_db();
    my $sth = do_sql($db, $ARGV[1]);
    show_data_table($sth);
    close_db($db);
} elsif ( $info eq "pw" ){
    # encrypt passwd
    print encrypt_passwd($ARGV[1]);
} elsif ( $info eq "auth" ){
    # encrypt passwd
    my $pwd = "7e171MAkxjvuE";
    my $word = $ARGV[1];
    if ( crypt($word,$pwd) eq $pwd ){
	print "matched\n";
    } else {
	print "unmatched\n";
    }
} elsif ( $info eq "basename" ){
    my($base, $dir ) = fileparse "/a/b/c/d/e.f";
    print "base=$base, dir=$dir\n";
} else {
    show_head();
    show_info($x,$y,$tsq,$vel, 0);

#    show_head();
#    print "cmd=", $ARGV[0], "\n";
#    my $file = "poi.html";
#    my $next;
#    ($lp, $next) = do_parse_file($file);

#    print "$next\n";
#    my @poi = @$lp;
#    my $cnt = $#poi;
#    print "count= $cnt\n";
#    show_data($lp);
}

if ( !$inline ){
    show_comment_form();
    show_last_comment();

    show_tail();
}

#
# EOF
#
# oracle mysql: go_hodaka/F15eagle
#
=pod
  Note
=cut
