<?php


use LibreNMS\Authentication\LegacyAuth;

if (!LegacyAuth::user()->hasGlobalAdmin()) {
    $status = array('status' =>1, 'message' => 'ERROR: You need to be admin to delete poller entries');
} else {
    $id = $vars['id'];
    if (!is_numeric($id)) {
        $status = array('status' =>1, 'message' => 'No poller has been selected');
    } else {
        $poller_name = dbFetchCell('SELECT `poller_name` FROM `distributed_poller` WHERE `id`=?', array($id));
        if (dbDelete('distributed_poller', 'id=?', array($id))) {
            $status = array('status' => 0, 'message' => "Poller: <i>$poller_name ($id), has been deleted.</i>");
        } else {
            $status = array('status' => 1, 'message' => "Poller: <i>$poller_name ($id), has NOT been deleted.</i>");
        }
    }
}
header('Content-Type: application/json');
echo _json_encode($status);
