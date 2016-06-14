#!/usr/bin/perl
#
# mana.cgi
#
# Travian CGI Main ANAlyzer
#
# $Id$
#

#map.sql: z,x,y,tribe,vid,village,uid,user,aid,alliance,population

use strict;
use CGI::Carp qw(fatalsToBrowser);

use Digest::MD5 qw(md5_hex);

use DBI;
use utf8;
use DBD::mysql;
#use CGI;

#use HTTP::REQUEST;
use LWP::UserAgent;

#
# Globals
#
my $prog   = 'mana.cgi';
#
my $dbname = 'qshino';
my $host   = 'localhost';
my $user   = 'qshino';
my $passwd = 'f15eagle';

my $table  = 'map20160508';
my $list   = 'maplist';
my $xtable = 'x_world';

my $server = 'http://ts4.travian.jp';
my $map_url = $server . "/map.sql";
#
# init for DB
#
sub init_db {
    my $q = "";

    my $db = open_db();

    $q = "create table maplist (id serial, mapname varchar(32), timestamp timestamp, note varchar(256));";
    do_sql($db, $q);

    $q = "create table x_world (z int, x int, y int, tribe int, vid int, village varchar(128), uid int, user varchar(128), aid int, alliance varchar(128), population int);";
    do_sql($db, $q);

    close_db($db);
    return 0;
}

    
sub show_head {
  print "Content-type:text/html; charset=utf-8\n\n";
  print '<html>';
  print '<head>';
  print '<title> Travian Utilities </title>';

  print '</head>';
  print '<body>';

  my $info = $ENV{"PATH_INFO"};

  print "<p>";

  print "<a href=\"/\">Top</a> ";
  print "| <a href=\"/$prog/menu\">menu</a> ";
  print "| <a href=\"/$prog/query\">query</a>";
  print "| <a href=\"/$prog/map\">map</a> ";
  print "| <a href=\"/$prog/load\">load_map</a> ";
  print "| <a href=\"/$prog/load_force\">force to load</a> ";
  print "| <a href=\"/kuma.cgi\">narusa</a>";
  print "| <a href=\"/$prog$info\">reload</a>";

  print "</p> ";
}

sub show_tables {
    my($db) = @_;

    my $sth = do_sql($db, "show tables;");

    my $num_rows = $sth->rows;

    print '<h2> Tables </h2>';
    print "Found $num_rows rows<br>\n";

    print "<table border=1>\n";
    
    for (my $i=0; $i<$num_rows; $i++) {
	my @a = $sth->fetchrow_array;
	print "<tr>";
	foreach my $x (@a){   print "<td>$x</td>";}
	print "</tr>\n";
    }
    print "</table>\n";
    $sth->finish;
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

sub do_sql {
    my($db, $q) = @_;

    my $sth = $db->prepare($q);
    $sth->execute();
#    $db->commit();

    return $sth;
}

sub run_sql {
    my($q) = @_;

    my $db = open_db();
    my $sth = do_sql($db, $q);

    close_db($db);

    return $sth;
}
    

sub show_maplist {
    my ($db) = @_;
    
    my $sth = do_sql($db, "select * from $list order by id desc limit 5;");

    my $num_rows = $sth->rows;

    print '<h2> Last Tables </h2>';
    print "Found $num_rows rows<br>\n";

    print "<table border=1>\n";
    
    for (my $i=0; $i<$num_rows; $i++) {
	my @a = $sth->fetchrow_array;
	print "<tr>";
	foreach my $x (@a){   print "<td>$x</td>";}
	print "</tr>\n";
    }
    print "</table>\n";
    $sth->finish;
}

sub show_form {
    my($query) = @_;
    
    my $cgi = $prog;

    $query = "select * from $xtable limit 3;" if ( !$query );
    
    print "<form method=\"post\" action=\"/$cgi\">\n";
    print "<textarea name=sql rows=\"6\" cols=\"80\">$query</textarea>\n";
    print "<input type=submit name=go value=exec>\n";

    print "<input type=submit name=go value=save>\n";
    print "</form>\n";
}    

sub show_form_load {
    my($query) = @_;
    
    my $cgi = $prog;

    $query = "select * from $xtable;" if ( !$query );
    
    print "<form method=\"post\n action=\"/$cgi\">\n";
    print "<input type=submit name=load value=load>\n";
    print "</form>\n";
}    

sub save_query {
    # queries: id, timestamp, note, query
    my($db, $query) = @_;
    
    my $note = $prog;

    my $sth = do_sql($db, "insert into queries ( note, query ) values (\"$note\", \"$query\" )");

    $sth->finish;
}

sub show_query_list {
    my($db) = @_;
    
    my $sth = do_sql($db, "select * from queries order by id desc;" );

    print '<h2> Query list </h2>';

    show_data_table($sth, \&item_link_query);
    $sth->finish;
}

sub item_func {
    my($a) = @_;

    return $a;
}

sub item_link_del {
    my($x) = @_;

    return "<a href=\"/$prog/delete/$x\">$x</a>";
}

sub item_link_query {
    my($x) = @_;

    return "<a href=\"/$prog/query/$x\">$x</a>";
}

sub show_data_table {
    my($sth,$func) = @_;
    
    my $num_rows = $sth->rows;

    print "Found $num_rows rows<br>\n";
    print "<table border=1>\n";

    my $ap = $sth->{NAME};
    print join("", map {"<th>".$_."</th>"} @$ap),"\n";

    for (my $i=0; $i<$num_rows; $i++) {
	my @a = $sth->fetchrow_array;

	print "<tr>";

	my $virgin = 1;
	foreach my $x (@a){
	    if( $virgin == 1 && defined($func) ){
		$x = &$func($x);
		$virgin = 0;
	    } 
	    print "<td>$x</td>"; 
	}
	print "</tr>\n";
    }
    print "</table>\n";
}

sub show_content {
    my($db, $q) = @_;

    my $query = "select * from $table where user = 'zolo'";
    my $query = $q if ($q);
 
    my $sth = do_sql($db, $query);

    print '<h2> Query </h2>';

    show_data_table($sth);
    $sth->finish;
}

sub do_insert {
    my( $db, $sql, $md5, $force ) = @_;

    my ($sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst)
	= localtime(time);
    $year += 1900;
    $mon += 1;

    
    #
    # check existance
    #
    my $suf = "";
    my $maxcnt = 10;
    my $nrows;
    my $newtable;
    
    for(my $iter=0;$iter<$maxcnt;$iter++){
	$newtable = sprintf "map%04d%02d%02d%s", $year, $mon, $mday, $suf;
	my $sth = do_sql($db, "show tables like \'$newtable\';");
	$nrows = $sth->rows;
	$sth->finish;

	if( $suf eq "" ){ $suf = "a";}
	else {
	    $suf = chr(ord($suf)+1);
	}
	if( $nrows <= 0 ){ last; }
    } # end for

    if( $nrows > 0 ){
	# table already exists.
	print "$newtable has already existed.\n";
	if( !defined($force) || $force == 0 ){
	    return 2;
	}
	print "Continue to load by dropping last table because of forced mode.\n";
	my $ret = $db->do("drop table $newtable;");
    } # if
    #
    # truncate $xtable
    #
    $nrows = $db->do( "truncate table $xtable;" );

    if( $nrows == undef ){
	my $es = $db->errstr();
	# print "failed to truncate $xtable.($es)\n";
    }
    #
    # execute map.sql
    #
    foreach my $line (split(/\n/, $sql)){
	$db->do($line);
    }
    my $rows = $db->do( "create table $newtable as select * from $xtable;" );
    #
    # count
    #
    my $sth   = do_sql($db, "select count(*) from $xtable;");
    my ($cnt) = $sth->fetchrow_array;
    $sth->finish;

    # table maplist
    # id/auto, mapname/varchar(32), timestamp, note

    my $note = "$prog";
    
    $rows = $db->do("insert into $list ( mapname,note,cnt,md5 ) values (\'$newtable\', \'$note\', $cnt, \'$md5\');");

    print "<h2> New table </h2>\n";
    print "New table $newtable was created.\n";
    print "maplist $list cnt=$cnt note=$note\n";

    return 0;
}

sub show_tail {
    print '</body>';
    print '</html>';
}

sub get_html {
    my($url) = @_;

    my $ua = LWP::UserAgent->new();

    $ua->timeout(30);
    $ua->agent('Mozilla');

    #GET、PUT、POST、DELETE、HEADのいずれかを指定（httpsの場合はhttpsにするだけ）
    my $req = HTTP::Request->new(GET => $url);

#    $req->referer('http://referrer.ksknet.net');

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

# info : PATH_INFO

sub do_query {
    my($info) = @_;
    
    show_head();

    my $mode = 1;
    my $sql = "";
    my $save = "";
    
    my $db = open_db();

    if ( $info =~ /query\/(\d+)/ ){
	my $ix = $1;

	my $sth = do_sql($db, "select query from queries where id = $ix;");
	my @aaa = $sth->fetchrow_array();
	$sql = shift @aaa;
	$mode = 0 if ( $sql !~ /^select/ );

    } elsif ( $info =~ /query\/(\w+)/ ){
	my $qname = $1;
	my $sth = do_sql($db, "select query from queries where note = \"$qname\";");
	my @aaa = $sth->fetchrow_array();
	$sth->finish;
	$sql = shift @aaa;
	$mode = 0 if ( $sql !~ /^select/ ); 
    } else {
	use CGI;
	my $cgi  = CGI->new();
	$sql  = $cgi->param("sql");
	$save = $cgi->param("go");

	$sql = "" if (!defined($sql));
    }

    if ( $save eq "save" ){
	# save current query
	save_query($db, $sql);
	show_form($sql);
    }

    show_content($db, $sql) if ( $mode );

    # show query form
    show_form($sql);

    # show query list
    show_query_list($db);

    close_db($db);

    show_tail();
}

sub do_load {
    my($cmd, $forced) = @_;

    $forced = 0 if( !defined($forced) );
    
    my $ret = 0;
    
    show_head();

#    print "loading\n";

    my $db = open_db();

    if( $cmd eq "load" ){
	my $html = get_html($map_url);
	my $md5 = md5_hex($html);
	my ($oldmd5) = $db->selectrow_array("select md5 from $list order by id desc limit 1 ");

	if( $md5 ne $oldmd5 || $forced ){
	    $ret = do_insert($db, $html, $md5, $forced );
	} else {
	    print "map.sql has not been changed from the last load($md5).";
	}
	

    }

    show_tables($db);
    show_maplist($db);
    show_form_load();

    close_db($db);
    
    show_tail();

    return $ret;
}

sub do_delete {
    my($info) = @_;

    my($del,$ix) = split(/\//, $info);
    run_sql("delete from queries where id = $ix;");

    return 0;
}

sub do_paste {
    my($info) = @_;

    my($del,$ix) = split(/\//, $info);

    my $sth = run_sql("select query from queries where id = $ix ;");
    my @sqls = $sth->fetchrow_array;
    my $sql = shift @sqls;

    do_query($info);

    return 0;
}

#
# menu table
# id serial, name varchar(128), url varchar(128)
#
#
# create table menu (id serial, name varchar(128), url varchar(128));
#
# insert into menu (name,url) values ('menu','menu');
# insert into menu (name,url) values ('query','query');
# insert into menu (name,url) values ('art_hour','query/art_hour');
# insert into menu (name,url) values ('map','map');
# insert into menu (name,url) values ('load','load');
# insert into menu (name,url) values ('tsuyoi','query/41');
#
sub do_menu {

    show_head();
    
    my $sql = "select * from menu;";
    my $sth = run_sql($sql);

    my $num_rows = $sth->rows;

    my @menus = ();
    
    for (my $i=0; $i<$num_rows; $i++) {
	my $ap = $sth->fetchrow_arrayref;
	my $ap2 = [@$ap];
	push @menus, $ap2;
    }
    my $ix = 0;
    
    foreach my $ap (@menus){
	if( $ix % 5 == 0 ){
	    print "<h3> next items </h3>\n";
	}
	$ix++;
	
	my($id, $name,$url) = @$ap;
	print "||<a href=\"$url\">$name</a>";
    }
    show_tail();
    return 0;
}

sub handle_cmd {
    my ($cmd) = @_;
    
    my $ret = 0;
    
    use CGI;

    my $info = $ENV{"PATH_INFO"};
    $info =~ s/^\///;

    if( $cmd ne "" && $info eq "" ){
	$info = $cmd;
    }

    my $q           = CGI->new();
    my $button      = $q->param("load");

#    print "info = $info, cmd = $cmd\n";
    
    if( $button eq "load" || $info eq "load" ){
	$ret = do_load("load", 0);
    } elsif( $info eq "load_force" ){
	$ret = do_load("load", 1);
    } elsif ( $info =~ /init/ ){
	$ret = init_db();
    } elsif ( $info =~ /query/ ){
	$ret = do_query($info);
    } elsif ( $info eq "map" ){
	$ret = do_load("map", 0);
    } elsif ( $info =~ /^delete/ ){
	$ret = do_delete($info);
    } elsif ( $info =~ /^paste/ ){
	$ret = do_paste($info);
    } elsif ( $info =~ /^menu/ ){
	$ret = do_menu($info);
    } else {
	print "unknown command: $info\n";
    }
    return $ret;
}

#
# Main
#

my $cmd = "";
$cmd = "query";

if ( $#ARGV >= 0 ){
    $cmd = $ARGV[0];
#    print "argc=",$#ARGV,"\n";;
}

my $ret = handle_cmd($cmd);
exit($ret);

#
# EOF
#

#
# inact table
# create table inact (uid int uniq not null, popuation int, found date default curdate(), recovered date, note varchar(128), inactive boolean true, used boolean default false );
#
# update_inact (lastt varchar(32) , prevt vcarchar(32), first date)
# 
# step 1: insert
# step 2: update recovered

# create table inact (uid int not null unique, population int, found timestamp default current_timestamp, recovered date, note varchar(128), inactive bool default 1, used bool default 0 );
