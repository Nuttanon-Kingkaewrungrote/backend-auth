<?php
/*
 * Fund Auth v5 - Complete Auth System
 * 
 * Features:
 * - Login / Register (GreenShift forms)
 * - Navbar: เปลี่ยนปุ่ม "เข้าสู่ระบบ" เป็นชื่อ user + dropdown menu
 * - Logout ใช้งานได้
 * - Profile page support
 * 
 * ⚠️ ปิด snippet เก่าทั้งหมดก่อน
 * แก้ FUND_BACKEND บรรทัดข้างล่าง
 */

define('FUND_BACKEND', 'https://YOUR_NGROK_URL.ngrok-free.app');


// ============================================================
// PHP HANDLERS
// ============================================================

// LOGIN
add_action('wp_ajax_nopriv_fund_login', 'fund_v5_login');
add_action('wp_ajax_fund_login', 'fund_v5_login');
function fund_v5_login() {
    $remember = isset($_POST['remember']) && $_POST['remember'] == '1';
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/login', array(
        'headers' => array('Content-Type' => 'application/json', 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('username' => $_POST['username'], 'password' => $_POST['password'], 'remember_me' => $remember)),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code >= 500) { wp_send_json_error(array('error' => 'เซิร์ฟเวอร์มีปัญหา กรุณาลองใหม่ภายหลัง', 'error_type' => 'server')); return; }
    if ($code == 200 && isset($body['token'])) {
        $cookie_days = $remember ? 30 : 1;
        setcookie('auth_api_token', $body['token'], time() + 86400 * $cookie_days, '/');
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}

// REGISTER
add_action('wp_ajax_nopriv_fund_register', 'fund_v5_register');
add_action('wp_ajax_fund_register', 'fund_v5_register');
function fund_v5_register() {
    $email = sanitize_email($_POST['email']);
    $username = sanitize_text_field($_POST['username']);
    if (empty($username)) $username = explode('@', $email)[0];
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/register', array(
        'headers' => array('Content-Type' => 'application/json', 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('username' => $username, 'email' => $email, 'password' => $_POST['password'])),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200 && !isset($body['error'])) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// LOGOUT
add_action('wp_ajax_fund_logout', 'fund_v5_logout');
add_action('wp_ajax_nopriv_fund_logout', 'fund_v5_logout');
function fund_v5_logout() {
    setcookie('auth_api_token', '', time() - 3600, '/');
    wp_send_json_success(array('message' => 'ok'));
}

// VERIFY TOKEN
add_action('wp_ajax_fund_verify', 'fund_v5_verify');
add_action('wp_ajax_nopriv_fund_verify', 'fund_v5_verify');
function fund_v5_verify() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    if (!$token) { wp_send_json_error(array('message' => 'no token')); return; }
    $r = wp_remote_get(FUND_BACKEND . '/api/auth/verify', array(
        'headers' => array('Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// PROFILE
add_action('wp_ajax_fund_profile', 'fund_v5_profile');
add_action('wp_ajax_nopriv_fund_profile', 'fund_v5_profile');
function fund_v5_profile() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    if (!$token) { wp_send_json_error(array('message' => 'no token')); return; }
    $r = wp_remote_get(FUND_BACKEND . '/api/auth/profile', array(
        'headers' => array('Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// FORGOT PASSWORD
add_action('wp_ajax_nopriv_fund_forgot', 'fund_v5_forgot');
add_action('wp_ajax_fund_forgot', 'fund_v5_forgot');

// ACCOUNT INFO (profile + linked accounts)
add_action('wp_ajax_fund_account_info', 'fund_v5_account_info');
add_action('wp_ajax_nopriv_fund_account_info', 'fund_v5_account_info');
function fund_v5_account_info() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    if (!$token) { wp_send_json_error(array('message' => 'no token')); return; }
    $r = wp_remote_get(FUND_BACKEND . '/api/auth/account-info', array(
        'headers' => array('Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// CHANGE PASSWORD
add_action('wp_ajax_fund_change_pw', 'fund_v5_change_pw');
function fund_v5_change_pw() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/change-password', array(
        'headers' => array('Content-Type' => 'application/json', 'Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('current_password' => $_POST['current_password'], 'new_password' => $_POST['new_password'])),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200 && !isset($body['error'])) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// SET PASSWORD (Google-only user)
add_action('wp_ajax_fund_set_pw', 'fund_v5_set_pw');
function fund_v5_set_pw() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/set-password', array(
        'headers' => array('Content-Type' => 'application/json', 'Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('new_password' => $_POST['new_password'])),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200 && !isset($body['error'])) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// LINK GOOGLE
add_action('wp_ajax_fund_link_google', 'fund_v5_link_google');
function fund_v5_link_google() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $credential = sanitize_text_field($_POST['credential']);
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/link-google', array(
        'headers' => array('Content-Type' => 'application/json', 'Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('credential' => $credential)),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// UNLINK GOOGLE
add_action('wp_ajax_fund_unlink_google', 'fund_v5_unlink_google');

// UPDATE PROFILE (display_name)
add_action('wp_ajax_fund_update_profile', 'fund_v5_update_profile');
function fund_v5_update_profile() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/update-profile', array(
        'headers' => array('Content-Type' => 'application/json', 'Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('display_name' => $_POST['display_name'])),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// UPLOAD AVATAR
add_action('wp_ajax_fund_upload_avatar', 'fund_v5_upload_avatar');
function fund_v5_upload_avatar() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    if (!isset($_FILES['avatar'])) { wp_send_json_error(array('message' => 'No file')); return; }
    
    $file = $_FILES['avatar'];
    $boundary = wp_generate_password(24);
    
    // สร้าง multipart body
    $body = '';
    $body .= '--' . $boundary . "\r\n";
    $body .= 'Content-Disposition: form-data; name="file"; filename="' . $file['name'] . '"' . "\r\n";
    $body .= 'Content-Type: ' . $file['type'] . "\r\n\r\n";
    $body .= file_get_contents($file['tmp_name']) . "\r\n";
    $body .= '--' . $boundary . '--' . "\r\n";
    
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/upload-avatar', array(
        'headers' => array(
            'Content-Type' => 'multipart/form-data; boundary=' . $boundary,
            'Authorization' => 'Bearer ' . $token,
            'ngrok-skip-browser-warning' => 'true'
        ),
        'body' => $body,
        'timeout' => 30
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $resp = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($resp); } else { wp_send_json_error($resp); }
}
function fund_v5_unlink_google() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';
    $r = wp_remote_request(FUND_BACKEND . '/api/auth/unlink/google', array(
        'method' => 'DELETE',
        'headers' => array('Authorization' => 'Bearer ' . $token, 'ngrok-skip-browser-warning' => 'true'),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// GOOGLE LOGIN URL
add_action('wp_ajax_nopriv_fund_google_url', 'fund_v5_google_url');
add_action('wp_ajax_fund_google_url', 'fund_v5_google_url');
function fund_v5_google_url() {
    $r = wp_remote_get(FUND_BACKEND . '/api/auth/google/url', array(
        'headers' => array('ngrok-skip-browser-warning' => 'true'),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    wp_send_json_success($body);
}

// GOOGLE VERIFY TOKEN (popup flow)
add_action('wp_ajax_nopriv_fund_google_verify', 'fund_v5_google_verify');
add_action('wp_ajax_fund_google_verify', 'fund_v5_google_verify');
function fund_v5_google_verify() {
    $credential = sanitize_text_field($_POST['credential']);
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/google/verify', array(
        'headers' => array('Content-Type' => 'application/json', 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('credential' => $credential)),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200 && isset($body['token'])) {
        setcookie('auth_api_token', $body['token'], time() + 86400 * 30, '/');
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}

// GOOGLE CALLBACK (set cookie from token)
add_action('wp_ajax_nopriv_fund_google_set', 'fund_v5_google_set');
add_action('wp_ajax_fund_google_set', 'fund_v5_google_set');
function fund_v5_google_set() {
    $token = sanitize_text_field($_POST['token']);
    if (!$token) { wp_send_json_error(array('message' => 'no token')); return; }
    setcookie('auth_api_token', $token, time() + 86400 * 30, '/');
    wp_send_json_success(array('message' => 'ok'));
}
function fund_v5_forgot() {
    $email = sanitize_email($_POST['email']);
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/forgot-password', array(
        'headers' => array('Content-Type' => 'application/json', 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('email' => $email)),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}

// RESET PASSWORD
add_action('wp_ajax_nopriv_fund_reset_pw', 'fund_v5_reset_pw');
add_action('wp_ajax_fund_reset_pw', 'fund_v5_reset_pw');
function fund_v5_reset_pw() {
    $token = sanitize_text_field($_POST['token']);
    $password = $_POST['password'];
    $r = wp_remote_post(FUND_BACKEND . '/api/auth/reset-password', array(
        'headers' => array('Content-Type' => 'application/json', 'ngrok-skip-browser-warning' => 'true'),
        'body' => json_encode(array('token' => $token, 'new_password' => $password)),
        'timeout' => 15
    ));
    if (is_wp_error($r)) { wp_send_json_error(array('error' => 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', 'error_type' => 'connection')); return; }
    $body = json_decode(wp_remote_retrieve_body($r), true);
    $code = wp_remote_retrieve_response_code($r);
    if ($code == 200 && !isset($body['error'])) { wp_send_json_success($body); } else { wp_send_json_error($body); }
}


// ============================================================
// CSS + JAVASCRIPT
// ============================================================
add_action('wp_enqueue_scripts', function(){ wp_enqueue_script('jquery'); });

add_action('wp_footer', 'fund_v5_script');
function fund_v5_script() {
    ?>
<style>
/* User Menu Dropdown */
.fund-user-menu {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    padding: 5px 12px;
    border-radius: 25px;
    transition: background 0.2s;
}
.fund-user-menu:hover { background: rgba(0,0,0,0.05); }

.fund-user-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: bold; font-size: 14px;
    margin-right: 8px;
    flex-shrink: 0;
}

.fund-user-name {
    font-weight: 600;
    font-size: 14px;
    color: #333;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.fund-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 8px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    min-width: 220px;
    z-index: 99999;
    display: none;
    overflow: hidden;
    border: 1px solid #e5e7eb;
}
.fund-dropdown.open { display: block; }

.fund-dropdown-header {
    padding: 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}
.fund-dropdown-header .name { font-weight: 700; font-size: 15px; }
.fund-dropdown-header .email { font-size: 12px; opacity: 0.85; margin-top: 2px; }

.fund-dropdown a {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    color: #374151;
    text-decoration: none;
    font-size: 14px;
    transition: background 0.15s;
    border-bottom: 1px solid #f3f4f6;
}
.fund-dropdown a:hover { background: #f9fafb; }
.fund-dropdown a:last-child { border-bottom: none; }
.fund-dropdown a .icon { margin-right: 10px; font-size: 16px; }

.fund-dropdown a.logout-link { color: #ef4444; }
.fund-dropdown a.logout-link:hover { background: #fef2f2; }
</style>

<script>
(function(){
    'use strict';

    var AJAX = '<?php echo admin_url("admin-ajax.php"); ?>';
    var busy = false;
    var PROFILE_URL = '/profile/';

    function log(m){ console.log('[FundAuth] ' + m); }

    function msg(t, ok){
        var d = document.getElementById('fa-msg');
        if(d) d.remove();
        d = document.createElement('div');
        d.id = 'fa-msg';
        d.textContent = t;
        d.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:999999;padding:15px 30px;border-radius:8px;font-size:16px;font-weight:bold;box-shadow:0 4px 12px rgba(0,0,0,.15);' + (ok ? 'background:#d4edda;color:#155724;' : 'background:#f8d7da;color:#721c24;');
        document.body.appendChild(d);
        setTimeout(function(){ if(d.parentNode) d.remove(); }, 5000);
    }

    function getCookie(n){
        var m = document.cookie.match(new RegExp('(^| )' + n + '=([^;]+)'));
        return m ? m[2] : null;
    }


    // ================================================================
    // NAVBAR: เปลี่ยนปุ่ม "เข้าสู่ระบบ" เป็น Profile Icon
    // ================================================================
    function initNavbar(){
        var token = getCookie('auth_api_token');
        var user = null;
        try { user = JSON.parse(localStorage.getItem('auth_user')); } catch(e){}

        if(!token || !user){
            log('Not logged in');
            return;
        }

        var displayName = user.display_name || user.username;
        log('Logged in as: ' + displayName);

        var navWrapper = null;
        var navBtn = null;
        document.querySelectorAll('a.gspb-buttonbox, a.wp-element-button').forEach(function(a){
            var t = (a.textContent||'').trim();
            var href = decodeURIComponent(a.getAttribute('href')||'');
            if(t === 'เข้าสู่ระบบ' && href.indexOf('เข้าสู่ระบบ') !== -1){
                navBtn = a;
                navWrapper = a.closest('.gspb_button_wrapper') || a.parentElement;
            }
        });

        if(!navBtn || !navWrapper){
            log('No navbar login button found');
            return;
        }

        log('Replacing navbar button');

        var initial = (displayName||'U').charAt(0).toUpperCase();
        var email = user.email || '';
        var avatarUrl = user.avatar_url;

        // สร้าง profile icon
        var avatarContent = '';
        if(avatarUrl){
            var imgSrc = avatarUrl.startsWith('http') ? avatarUrl : '<?php echo FUND_BACKEND; ?>' + avatarUrl;
            avatarContent = '<img src="' + imgSrc + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" onerror="this.style.display=\'none\';this.parentElement.textContent=\'' + initial + '\'">';
        } else {
            avatarContent = initial;
        }

        var el = document.createElement('div');
        el.style.cssText = 'position:relative;display:inline-block;';
        el.innerHTML = ''
            + '<div id="fund-nav-trigger" style="cursor:pointer;width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:16px;box-shadow:0 2px 8px rgba(102,126,234,0.4);transition:transform 0.2s;overflow:hidden;">'
            + avatarContent
            + '</div>'
            + '<div id="fund-nav-dropdown" class="fund-dropdown">'
            + '  <div class="fund-dropdown-header">'
            + '    <div class="name">' + displayName + '</div>'
            + '    <div class="email">' + (email||'') + '</div>'
            + '  </div>'
            + '  <a href="/profile/">'
            + '    <span class="icon">👤</span> จัดการโปรไฟล์'
            + '  </a>'
            + '  <a href="#" id="fund-nav-logout" class="logout-link">'
            + '    <span class="icon">🚪</span> ออกจากระบบ'
            + '  </a>'
            + '</div>';

        navWrapper.parentNode.replaceChild(el, navWrapper);

        var trigger = document.getElementById('fund-nav-trigger');
        trigger.addEventListener('mouseenter', function(){ this.style.transform='scale(1.1)'; });
        trigger.addEventListener('mouseleave', function(){ this.style.transform=''; });

        var dd = document.getElementById('fund-nav-dropdown');
        trigger.addEventListener('click', function(e){
            e.stopPropagation();
            dd.classList.toggle('open');
        });
        document.addEventListener('click', function(){ dd.classList.remove('open'); });

        document.getElementById('fund-nav-logout').addEventListener('click', function(e){
            e.preventDefault();
            doLogout();
        });

        log('Navbar updated OK');
    }


    // ================================================================
    // LOGIN PAGE
    // ================================================================
    function initLogin(){
        // === เช็ค Google callback token ใน URL ===
        var params = new URLSearchParams(window.location.search);
        var gToken = params.get('google_token');
        var gUser = params.get('google_user');
        var gError = params.get('error');

        if(gError){
            log('Google login error: ' + gError);
            msg('เข้าสู่ระบบด้วย Google ไม่สำเร็จ กรุณาลองใหม่', false);
            // ลบ query params
            window.history.replaceState({}, '', window.location.pathname);
        }

        if(gToken && gUser){
            log('Google callback token received');
            try {
                var user = JSON.parse(decodeURIComponent(gUser));
                // Set cookie ผ่าน PHP
                jQuery.post(AJAX, {action:'fund_google_set', token:gToken}, function(res){
                    if(res.success){
                        localStorage.setItem('auth_user', JSON.stringify(user));
                        var welcomeName = user.display_name || user.username;
                        msg('เข้าสู่ระบบด้วย Google สำเร็จ! ยินดีต้อนรับ ' + welcomeName, true);
                        setTimeout(function(){ window.location.href='/'; }, 1200);
                    }
                });
            } catch(e){
                log('Failed to parse Google user: ' + e);
            }
            return;
        }

        // === ถ้า login อยู่แล้ว redirect ===
        var token = getCookie('auth_api_token');
        if(token){
            var user = null;
            try { user = JSON.parse(localStorage.getItem('auth_user')); } catch(e){}
            if(user){
                log('Already logged in'); safeRedirect('/');
                return;
            }
        }

        var form = document.querySelector('form[class*="gsbp-"]');
        if(!form){ log('No form'); return; }

        var eml = form.querySelector('input[name="email"],input[type="email"]');
        var pwd = form.querySelector('input[name="password"],input[type="password"]');
        if(!eml || !pwd){ log('No inputs'); return; }

        // === หา checkbox "จดจำบัญชี" ===
        var rememberCb = document.querySelector('input[type="checkbox"]');
        if(rememberCb) log('Found remember checkbox');

        log('Form found OK');

        // === หาปุ่ม Login ===
        var btns = [];
        document.querySelectorAll('a, button').forEach(function(el){
            if((el.textContent||'').trim() === 'เข้าสู่ระบบ') btns.push(el);
        });
        log('Found ' + btns.length + ' login buttons');

        function doIt(e){
            if(e){ e.preventDefault(); e.stopImmediatePropagation(); }
            if(busy) return;
            var u = eml.value.trim(), p = pwd.value;
            if(!u||!p){ msg('กรุณากรอกอีเมลและรหัสผ่าน',false); return; }

            var remember = rememberCb ? rememberCb.checked : false;
            busy = true;
            log('Login: ' + u + ' remember=' + remember);
            btns.forEach(function(b){ b.style.opacity='0.5'; b.style.pointerEvents='none'; });

            jQuery.ajax({
                url: AJAX, method:'POST', timeout: 20000,
                data: {action:'fund_login', username:u, password:p, remember: remember ? 1 : 0},
                success: function(res){
                    log('Res: ' + JSON.stringify(res).substring(0,200));
                    if(res.success && res.data && res.data.token){
                        localStorage.setItem('auth_user', JSON.stringify(res.data.user));
                        var welcomeName = res.data.user.display_name || res.data.user.username;
                        msg('เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับ ' + welcomeName, true);
                        setTimeout(function(){ window.location.href='/'; }, 1200);
                    } else {
                        var m = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง';
                        var d = res.data || {};
                        m = d.detail||d.error||d.message||m;
                        if(typeof m === 'object') m = JSON.stringify(m);
                        msg(m, false);
                        reset();
                    }
                },
                error: function(x,s,e){
                    log('ERR: '+s+' '+e);
                    if(s==='timeout') msg('เซิร์ฟเวอร์ไม่ตอบสนอง กรุณาลองใหม่', false);
                    else msg('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง', false);
                    reset();
                }
            });

            function reset(){
                busy = false;
                btns.forEach(function(b){ b.style.opacity=''; b.style.pointerEvents=''; });
            }
        }

        btns.forEach(function(b){
            b.setAttribute('href','javascript:void(0)');
            b.addEventListener('click', doIt, true);
        });
        form.addEventListener('submit', doIt, true);
        eml.addEventListener('keydown', function(e){ if(e.key==='Enter') doIt(e); });
        pwd.addEventListener('keydown', function(e){ if(e.key==='Enter') doIt(e); });

        // === Google Login Button ===
        initGoogleButton();

        log('LOGIN READY');
    }

    // ================================================================
    // GOOGLE LOGIN BUTTON
    // ================================================================
    function initGoogleButton(){
        var googleBtn = document.getElementById('google-login-btn');
        if(!googleBtn){
            log('No Google button');
            return;
        }
        log('Found Google button — loading GIS');

        // โหลด Google Identity Services
        var script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.onload = function(){
            log('Google GIS loaded');
            jQuery.post(AJAX, {action:'fund_google_url'}, function(res){
                if(!res.success||!res.data||!res.data.url){ log('No Google URL'); return; }
                var match = res.data.url.match(/client_id=([^&]+)/);
                if(!match){ log('No client_id'); return; }
                var clientId = match[1];
                log('Client ID OK');

                google.accounts.id.initialize({
                    client_id: clientId,
                    callback: function(response){
                        log('Google credential received');
                        handleGoogleCredential(response.credential);
                    },
                    ux_mode: 'popup'
                });

                // แทนที่ icon เดิมด้วยปุ่ม Google ของ GIS
                googleBtn.innerHTML = '';
                google.accounts.id.renderButton(googleBtn, {
                    type: 'icon',
                    shape: 'circle',
                    size: 'large',
                    theme: 'outline'
                });

                log('Google button rendered');
            });
        };
        document.head.appendChild(script);
    }

    function handleGoogleCredential(credential){
        if(busy) return;
        busy = true;
        msg('กำลังเข้าสู่ระบบด้วย Google...', true);
        jQuery.ajax({
            url:AJAX, method:'POST', timeout:20000,
            data:{action:'fund_google_verify', credential:credential},
            success:function(res){
                log('Google verify: '+JSON.stringify(res).substring(0,200));
                if(res.success && res.data && res.data.token){
                    localStorage.setItem('auth_user', JSON.stringify(res.data.user));
                    msg('เข้าสู่ระบบด้วย Google สำเร็จ!', true);
                    setTimeout(function(){ window.location.href='/'; }, 1200);
                } else {
                    msg(res.data?.detail||res.data?.error||'Google login ไม่สำเร็จ', false);
                    busy=false;
                }
            },
            error:function(){ msg('เชื่อมต่อไม่ได้',false); busy=false; }
        });
    }


    // ================================================================
    // REGISTER PAGE
    // ================================================================
    function initRegister(){
        // ถ้า login อยู่แล้ว redirect
        var token = getCookie('auth_api_token');
        if(token){
            var user = null;
            try { user = JSON.parse(localStorage.getItem('auth_user')); } catch(e){}
            if(user){ safeRedirect('/'); return; }
        }

        var form = document.querySelector('form[class*="gsbp-"]');
        if(!form){ log('No register form'); return; }

        var inputs = form.querySelectorAll('input');
        var fields = { email:null, username:null, pwd:null, pwd2:null };
        inputs.forEach(function(i){
            var n=(i.name||'').toLowerCase(), t=(i.type||'').toLowerCase(), p=(i.placeholder||'').toLowerCase();
            if(t==='email'||n==='email'||p.includes('อีเมล')) fields.email=i;
            else if(n==='username'||p.includes('ชื่อผู้ใช้')) fields.username=i;
            else if(n.includes('confirm')||p.includes('ยืนยัน')) fields.pwd2=i;
            else if(t==='password'||n==='password'||p.includes('รหัสผ่าน')){
                if(!fields.pwd) fields.pwd=i; else if(!fields.pwd2) fields.pwd2=i;
            }
        });
        if(!fields.pwd || (!fields.email && !fields.username)){ log('Missing fields'); return; }

        log('Register fields OK');

        var btns = [];
        var texts = ['สมัครสมาชิก','สมัคร','เข้าสู่ระบบ','เข้าสู๋ระบบ'];
        document.querySelectorAll('a, button').forEach(function(el){
            var t=(el.textContent||'').trim();
            var href = el.getAttribute('href')||'';
            var ok = (href==='#'||href===''||href.indexOf('javascript:')===0||decodeURIComponent(href).indexOf('สมัครสมาชิก')!==-1);
            for(var s=0;s<texts.length;s++){ if(t===texts[s]&&ok){ btns.push(el); break; } }
        });
        log('Found '+btns.length+' register buttons');

        function doIt(e){
            if(e){ e.preventDefault(); e.stopImmediatePropagation(); }
            if(busy) return;
            var email=fields.email?fields.email.value.trim():'';
            var username=fields.username?fields.username.value.trim():'';
            var pass=fields.pwd.value, pass2=fields.pwd2?fields.pwd2.value:pass;
            if(!username&&email) username=email.split('@')[0];

            if(!username){ msg('กรุณากรอก Email',false); return; }
            if(!pass){ msg('กรุณากรอกรหัสผ่าน',false); return; }
            if(pass!==pass2){ msg('รหัสผ่านไม่ตรงกัน',false); return; }
            if(pass.length<6){ msg('รหัสผ่านต้องมีอย่างน้อย 6 ตัว',false); return; }
            if(email&&!email.includes('@')){ msg('อีเมลไม่ถูกต้อง',false); return; }

            busy=true;
            btns.forEach(function(b){ b.style.opacity='0.5'; b.style.pointerEvents='none'; });

            jQuery.ajax({
                url:AJAX, method:'POST', timeout:20000,
                data:{action:'fund_register',username:username,email:email,password:pass},
                success:function(res){
                    log('Res: '+JSON.stringify(res).substring(0,300));
                    if(res.success && res.data && !res.data.error && !res.data.detail){
                        msg(res.data.message||'สมัครสำเร็จ!', true);
                        setTimeout(function(){ window.location.href='/'+encodeURIComponent('เข้าสู่ระบบ')+'/'; }, 1500);
                    } else {
                        var m='สมัครไม่สำเร็จ', d=res.data||{};
                        if(d.detail){ m=Array.isArray(d.detail)?d.detail.map(function(x){return x.msg||JSON.stringify(x);}).join(', '):d.detail; }
                        else if(d.error) m=d.error;
                        if(typeof m==='object') m=JSON.stringify(m);
                        msg(m,false); reset();
                    }
                },
                error:function(x,s){ msg(s==='timeout'?'เซิร์ฟเวอร์ไม่ตอบสนอง กรุณาลองใหม่':'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง',false); reset(); }
            });

            function reset(){ busy=false; btns.forEach(function(b){ b.style.opacity=''; b.style.pointerEvents=''; }); }
        }

        btns.forEach(function(b){ b.setAttribute('href','javascript:void(0)'); b.addEventListener('click',doIt,true); });
        form.addEventListener('submit',doIt,true);
        inputs.forEach(function(i){ i.addEventListener('keydown',function(e){ if(e.key==='Enter') doIt(e); }); });

        log('REGISTER READY');
    }


    // ================================================================
    // PROFILE PAGE
    // ================================================================
    function initProfile(){
        var token = getCookie('auth_api_token');
        if(!token){
            safeRedirect('/'+encodeURIComponent('เข้าสู่ระบบ')+'/');
            return;
        }

        var page = document.getElementById('fund-profile-page');
        if(!page){ log('No #fund-profile-page'); return; }

        log('Loading account info...');

        jQuery.post(AJAX, {action:'fund_account_info', token:token}, function(res){
            log('Account info: '+JSON.stringify(res).substring(0,300));
            if(!res.success || !res.data || !res.data.user){
                // Token หมดอายุ — ลบ cookie + localStorage แต่ไม่ redirect
                document.cookie = 'auth_api_token=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT';
                localStorage.removeItem('auth_user');
                document.getElementById('fund-loading').innerHTML = '<div style="text-align:center;padding:40px;"><div style="font-size:24px;margin-bottom:8px;">⚠️</div>เซสชันหมดอายุ กรุณา<a href="/'+encodeURIComponent('เข้าสู่ระบบ')+'/" style="color:#667eea;">เข้าสู่ระบบ</a>อีกครั้ง</div>';
                return;
            }

            var u = res.data.user;
            var linked = res.data.linked_accounts || [];
            var googleLinked = linked.find(function(a){ return a.provider==='google'; });
            var initial = (u.username||'U').charAt(0).toUpperCase();

            document.getElementById('fund-loading').style.display = 'none';
            document.getElementById('fund-content').style.display = 'block';

            // === Avatar ===
            var avatarImg = document.getElementById('fund-avatar-img');
            var avatarInitial = document.getElementById('fund-avatar-initial');
            var initial = (u.display_name||u.username||'U').charAt(0).toUpperCase();

            if(u.avatar_url){
                // ถ้าเป็น URL เต็ม (Google) ใช้ตรงๆ ถ้าเป็น path ใช้ FUND_BACKEND
                var imgSrc = u.avatar_url.startsWith('http') ? u.avatar_url : '<?php echo FUND_BACKEND; ?>' + u.avatar_url;
                avatarImg.src = imgSrc;
                avatarImg.style.display = 'block';
                avatarInitial.style.display = 'none';
                avatarImg.onerror = function(){ this.style.display='none'; avatarInitial.style.display=''; };
            } else {
                avatarInitial.textContent = initial;
            }

            // คลิก avatar เพื่อ upload
            document.getElementById('fund-avatar-wrapper').addEventListener('click', function(){
                document.getElementById('fund-avatar-input').click();
            });
            document.getElementById('fund-avatar-input').addEventListener('change', function(){
                var file = this.files[0];
                if(!file) return;
                if(file.size > 2*1024*1024){ msg('ไฟล์ต้องไม่เกิน 2MB',false); return; }
                var fd = new FormData();
                fd.append('action','fund_upload_avatar');
                fd.append('token',token);
                fd.append('avatar',file);
                msg('กำลังอัพโหลดรูป...',true);
                jQuery.ajax({url:AJAX,method:'POST',data:fd,processData:false,contentType:false,success:function(r){
                    if(r.success && r.data && r.data.avatar_url){
                        msg('อัพโหลดรูปสำเร็จ!',true);
                        avatarImg.src='<?php echo FUND_BACKEND; ?>'+r.data.avatar_url+'?t='+Date.now();
                        avatarImg.style.display='block'; avatarInitial.style.display='none';
                        // อัพเดท localStorage
                        var su=JSON.parse(localStorage.getItem('auth_user')||'{}');
                        su.avatar_url=r.data.avatar_url; localStorage.setItem('auth_user',JSON.stringify(su));
                    } else { msg(r.data?.detail||r.data?.error||'อัพโหลดไม่สำเร็จ',false); }
                },error:function(){ msg('อัพโหลดไม่ได้',false); }});
            });

            // === Display Name ===
            var displayName = u.display_name || u.username;
            document.getElementById('fund-display-name').textContent = displayName;
            document.getElementById('fund-email').textContent = u.email || '';

            // คลิกชื่อเพื่อแก้
            document.getElementById('fund-name-display').addEventListener('click', function(){
                this.style.display='none';
                document.getElementById('fund-name-edit').style.display='block';
                var inp = document.getElementById('fund-name-input');
                inp.value = displayName;
                inp.focus(); inp.select();
            });
            document.getElementById('fund-name-cancel').addEventListener('click', function(){
                document.getElementById('fund-name-edit').style.display='none';
                document.getElementById('fund-name-display').style.display='inline-flex';
            });
            document.getElementById('fund-name-save').addEventListener('click', function(){
                var newName = document.getElementById('fund-name-input').value.trim();
                if(!newName){ msg('กรุณากรอกชื่อ',false); return; }
                jQuery.post(AJAX,{action:'fund_update_profile',token:token,display_name:newName},function(r){
                    if(r.success){
                        msg('เปลี่ยนชื่อสำเร็จ!',true);
                        document.getElementById('fund-display-name').textContent=newName;
                        document.getElementById('fund-name-edit').style.display='none';
                        document.getElementById('fund-name-display').style.display='inline-flex';
                        // อัพเดท localStorage
                        var su=JSON.parse(localStorage.getItem('auth_user')||'{}');
                        su.display_name=newName; localStorage.setItem('auth_user',JSON.stringify(su));
                    } else { msg(r.data?.detail||r.data?.error||'เปลี่ยนไม่สำเร็จ',false); }
                });
            });
            document.getElementById('fund-name-input').addEventListener('keydown',function(e){
                if(e.key==='Enter') document.getElementById('fund-name-save').click();
                if(e.key==='Escape') document.getElementById('fund-name-cancel').click();
            });
            document.getElementById('fund-info-username').textContent = u.username;
            document.getElementById('fund-info-email').textContent = u.email || 'ไม่ได้ตั้งอีเมล';
            document.getElementById('fund-info-created').textContent = u.created_at ? new Date(u.created_at).toLocaleDateString('th-TH',{year:'numeric',month:'short',day:'numeric'}) : '-';
            document.getElementById('fund-info-login').textContent = u.last_login ? new Date(u.last_login).toLocaleDateString('th-TH',{year:'numeric',month:'short',day:'numeric'}) : '-';

            // === Password ===
            var pwStatus = document.getElementById('fund-pw-status');
            var pwSection = document.getElementById('fund-pw-section');
            var pwForm = document.getElementById('fund-pw-form');

            if(u.has_password){
                pwStatus.innerHTML = '<span style="color:#22c55e;">✅ ตั้งแล้ว</span>';
                pwSection.innerHTML = '<button id="btn-change-pw" style="width:100%;padding:10px;border:1px solid #e0e0e0;border-radius:8px;background:white;cursor:pointer;font-size:14px;color:#374151;">เปลี่ยนรหัสผ่าน</button>';
                document.getElementById('btn-change-pw').addEventListener('click', function(){
                    this.style.display='none'; pwForm.style.display='block';
                    pwForm.innerHTML = '<input type="password" id="pw-old" placeholder="รหัสผ่านเดิม" style="width:100%;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:8px;box-sizing:border-box;font-size:14px;">'
                        + '<input type="password" id="pw-new" placeholder="รหัสผ่านใหม่ (6+ ตัว)" style="width:100%;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:8px;box-sizing:border-box;font-size:14px;">'
                        + '<input type="password" id="pw-confirm" placeholder="ยืนยันรหัสผ่านใหม่" style="width:100%;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:10px;box-sizing:border-box;font-size:14px;">'
                        + '<div style="display:flex;gap:8px;"><button id="pw-save" style="flex:1;padding:10px;border:none;border-radius:8px;background:#667eea;color:white;cursor:pointer;font-size:14px;">บันทึก</button>'
                        + '<button id="pw-cancel" style="flex:1;padding:10px;border:1px solid #e0e0e0;border-radius:8px;background:white;cursor:pointer;font-size:14px;">ยกเลิก</button></div>';
                    document.getElementById('pw-cancel').addEventListener('click', function(){ pwForm.style.display='none'; document.getElementById('btn-change-pw').style.display=''; });
                    document.getElementById('pw-save').addEventListener('click', function(){
                        var o=document.getElementById('pw-old').value,n=document.getElementById('pw-new').value,c=document.getElementById('pw-confirm').value;
                        if(!o){msg('กรุณากรอกรหัสผ่านเดิม',false);return;} if(n.length<6){msg('รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัว',false);return;} if(n!==c){msg('รหัสผ่านไม่ตรงกัน',false);return;}
                        jQuery.post(AJAX,{action:'fund_change_pw',token:token,current_password:o,new_password:n},function(r){
                            if(r.success){msg('เปลี่ยนรหัสผ่านสำเร็จ!',true);pwForm.style.display='none';document.getElementById('btn-change-pw').style.display='';}
                            else{msg(r.data?.detail||r.data?.error||'เปลี่ยนไม่สำเร็จ',false);}
                        });
                    });
                });
            } else {
                pwStatus.innerHTML = '<span style="color:#f59e0b;">⚠️ ยังไม่ได้ตั้ง</span>';
                pwSection.innerHTML = '<button id="btn-set-pw" style="width:100%;padding:10px;border:none;border-radius:8px;background:#667eea;color:white;cursor:pointer;font-size:14px;">ตั้งรหัสผ่าน</button>';
                document.getElementById('btn-set-pw').addEventListener('click', function(){
                    this.style.display='none'; pwForm.style.display='block';
                    pwForm.innerHTML = '<input type="password" id="pw-new" placeholder="รหัสผ่านใหม่ (6+ ตัว)" style="width:100%;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:8px;box-sizing:border-box;font-size:14px;">'
                        + '<input type="password" id="pw-confirm" placeholder="ยืนยันรหัสผ่าน" style="width:100%;padding:10px 14px;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:10px;box-sizing:border-box;font-size:14px;">'
                        + '<div style="display:flex;gap:8px;"><button id="pw-save" style="flex:1;padding:10px;border:none;border-radius:8px;background:#667eea;color:white;cursor:pointer;font-size:14px;">ตั้งรหัสผ่าน</button>'
                        + '<button id="pw-cancel" style="flex:1;padding:10px;border:1px solid #e0e0e0;border-radius:8px;background:white;cursor:pointer;font-size:14px;">ยกเลิก</button></div>';
                    document.getElementById('pw-cancel').addEventListener('click', function(){ pwForm.style.display='none'; document.getElementById('btn-set-pw').style.display=''; });
                    document.getElementById('pw-save').addEventListener('click', function(){
                        var n=document.getElementById('pw-new').value,c=document.getElementById('pw-confirm').value;
                        if(n.length<6){msg('ต้องมีอย่างน้อย 6 ตัว',false);return;} if(n!==c){msg('รหัสผ่านไม่ตรงกัน',false);return;}
                        jQuery.post(AJAX,{action:'fund_set_pw',token:token,new_password:n},function(r){
                            if(r.success){msg('ตั้งรหัสผ่านสำเร็จ!',true); pwForm.style.display='none'; document.getElementById('btn-set-pw').style.display=''; pwStatus.innerHTML='<span style="color:#22c55e;">✅ ตั้งแล้ว</span>';}
                            else{msg(r.data?.detail||r.data?.error||'ตั้งไม่สำเร็จ',false);}
                        });
                    });
                });
            }

            // === Google ===
            var gStatus = document.getElementById('fund-google-status');
            var gEmail = document.getElementById('fund-google-email');
            var gSection = document.getElementById('fund-google-section');

            if(googleLinked){
                gStatus.innerHTML = '<span style="color:#22c55e;">เชื่อมแล้ว</span>';
                gSection.innerHTML = ''
                    + '<div style="display:flex;align-items:center;gap:14px;padding:14px 16px;background:#fafafa;border:1px solid #eee;border-radius:10px;">'
                    + '  <div style="width:40px;height:40px;border-radius:50%;background:#f3f4f6;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
                    + '    <img src="https://developers.google.com/identity/images/g-logo.png" style="width:22px;height:22px;">'
                    + '  </div>'
                    + '  <div style="flex:1;min-width:0;">'
                    + '    <div style="font-size:14px;font-weight:500;color:#333;">Google</div>'
                    + '    <div style="font-size:12px;color:#888;overflow:hidden;text-overflow:ellipsis;">'+googleLinked.email+'</div>'
                    + '  </div>'
                    + '  <button id="btn-unlink-google" style="padding:7px 16px;border:1px solid #e0e0e0;border-radius:20px;background:white;cursor:pointer;font-size:13px;color:#555;white-space:nowrap;transition:all 0.2s;" onmouseover="this.style.borderColor=\'#ef4444\';this.style.color=\'#ef4444\'" onmouseout="this.style.borderColor=\'#e0e0e0\';this.style.color=\'#555\'">Unlink</button>'
                    + '</div>';
                document.getElementById('btn-unlink-google').addEventListener('click', function(){
                    if(!confirm('ยืนยันยกเลิกเชื่อม Google?')) return;
                    jQuery.post(AJAX,{action:'fund_unlink_google',token:token},function(r){
                        if(r.success){msg('ยกเลิกเชื่อม Google สำเร็จ',true); setTimeout(function(){location.reload();},1500);}
                        else{msg(r.data?.detail||r.data?.error||'ยกเลิกไม่สำเร็จ',false);}
                    });
                });
            } else {
                gStatus.innerHTML = '<span style="color:#999;">ยังไม่ได้เชื่อม</span>';
                gSection.innerHTML = ''
                    + '<div style="display:flex;align-items:center;gap:14px;padding:14px 16px;background:#fafafa;border:1px dashed #ddd;border-radius:10px;">'
                    + '  <div style="width:40px;height:40px;border-radius:50%;background:#f3f4f6;display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
                    + '    <img src="https://developers.google.com/identity/images/g-logo.png" style="width:22px;height:22px;opacity:0.4;">'
                    + '  </div>'
                    + '  <div style="flex:1;min-width:0;">'
                    + '    <div style="font-size:14px;color:#999;">Google</div>'
                    + '    <div style="font-size:12px;color:#bbb;">ยังไม่ได้เชื่อม</div>'
                    + '  </div>'
                    + '  <button id="btn-link-google" style="padding:7px 16px;border:1px solid #667eea;border-radius:20px;background:white;cursor:pointer;font-size:13px;color:#667eea;white-space:nowrap;transition:all 0.2s;" onmouseover="this.style.background=\'#667eea\';this.style.color=\'white\'" onmouseout="this.style.background=\'white\';this.style.color=\'#667eea\'">Link</button>'
                    + '</div>';

                document.getElementById('btn-link-google').addEventListener('click', function(e){
                    e.preventDefault();
                    var btn = this;
                    btn.textContent = '...';
                    btn.disabled = true;
                    jQuery.post(AJAX,{action:'fund_google_url'},function(res){
                        if(!res.success||!res.data||!res.data.url){ msg('เชื่อมต่อไม่ได้',false); btn.textContent='Link'; btn.disabled=false; return; }
                        var m=res.data.url.match(/client_id=([^&]+)/);
                        if(!m){ btn.textContent='Link'; btn.disabled=false; return; }
                        var clientId=m[1];

                        window._fundLinkGoogleDone = function(credential){
                            msg('กำลังเชื่อม Google...',true);
                            jQuery.post(AJAX,{action:'fund_link_google',token:token,credential:credential},function(r){
                                if(r.success){msg('เชื่อม Google สำเร็จ!',true); setTimeout(function(){location.reload();},1500);}
                                else{msg(r.data?.detail||r.data?.error||'เชื่อมไม่สำเร็จ',false);}
                            });
                        };

                        // เปิด popup
                        var w=420, h=500;
                        var left=(screen.width-w)/2, top=(screen.height-h)/2;
                        var popup = window.open('','google_link_popup','width='+w+',height='+h+',left='+left+',top='+top);
                        popup.document.write(
                            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Link Google</title>'
                            +'<script src="https://accounts.google.com/gsi/client"><\/script></head>'
                            +'<body style="display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:-apple-system,sans-serif;background:#fafafa;">'
                            +'<div style="text-align:center;background:white;padding:32px;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">'
                            +'<img src="https://developers.google.com/identity/images/g-logo.png" style="width:40px;height:40px;margin-bottom:12px;">'
                            +'<p style="margin:0 0 20px;color:#333;font-size:15px;">เลือก Google Account<br><span style="font-size:12px;color:#999;">เพื่อเชื่อมกับบัญชีของคุณ</span></p>'
                            +'<div id="g-btn"></div>'
                            +'</div>'
                            +'<script>'
                            +'google.accounts.id.initialize({client_id:"'+clientId+'",ux_mode:"popup",callback:function(r){'
                            +'  if(window.opener&&window.opener._fundLinkGoogleDone){window.opener._fundLinkGoogleDone(r.credential);}'
                            +'  window.close();'
                            +'}});'
                            +'google.accounts.id.renderButton(document.getElementById("g-btn"),{type:"standard",theme:"outline",size:"large",text:"continue_with",shape:"pill",width:250});'
                            +'<\/script></body></html>'
                        );
                        popup.document.close();
                        btn.textContent='Link'; btn.disabled=false;
                        var check=setInterval(function(){ if(popup.closed){clearInterval(check); btn.textContent='Link'; btn.disabled=false;} },500);
                    });
                });
            }

            // Logout
            document.getElementById('fund-btn-logout').addEventListener('click', function(){ doLogout(); });

        }).fail(function(){
            document.getElementById('fund-loading').innerHTML = '<div style="text-align:center;padding:40px;"><div style="font-size:24px;margin-bottom:8px;">❌</div>เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่</div>';
        });
    }




    // ================================================================
    // FORGOT PASSWORD PAGE
    // ================================================================
    function initForgotPassword(){
        var form = document.querySelector('form[class*="gsbp-"]');
        if(!form){ log('No forgot form'); return; }

        var emlInp = form.querySelector('input[name="email"],input[type="email"]');
        if(!emlInp){ log('No email input'); return; }

        log('Forgot password form OK');

        // หาปุ่ม
        var btns = [];
        document.querySelectorAll('a, button').forEach(function(el){
            var t=(el.textContent||'').trim();
            if(t.indexOf('ส่งลิงก์')!==-1 || t.indexOf('รีเซ็ต')!==-1 || t.indexOf('reset')!==-1){
                btns.push(el);
            }
        });
        // Fallback: หาปุ่มที่ href=# ใกล้ form
        if(btns.length===0){
            document.querySelectorAll('a[href="#"], a[href="javascript:void(0)"]').forEach(function(el){
                var t=(el.textContent||'').trim();
                if(t.length>2 && t.length<30) btns.push(el);
            });
        }
        log('Found '+btns.length+' forgot buttons');

        var sent = false;

        function doIt(e){
            if(e){ e.preventDefault(); e.stopImmediatePropagation(); }
            if(busy) return;
            var email = emlInp.value.trim();
            if(!email || !email.includes('@')){ msg('กรุณากรอกอีเมลที่ถูกต้อง',false); return; }

            busy = true;
            btns.forEach(function(b){ b.style.opacity='0.5'; b.style.pointerEvents='none'; });

            jQuery.ajax({
                url:AJAX, method:'POST', timeout:20000,
                data:{action:'fund_forgot', email:email},
                success:function(res){
                    log('Forgot res: '+JSON.stringify(res).substring(0,200));
                    sent = true;
                    // แสดง success ทุกกรณี (security: ไม่บอกว่า email มีหรือไม่)
                    showSentMessage(email);
                },
                error:function(){
                    msg('เชื่อมต่อไม่ได้ กรุณาลองใหม่',false);
                    busy=false;
                    btns.forEach(function(b){ b.style.opacity=''; b.style.pointerEvents=''; });
                }
            });
        }

        function showSentMessage(email){
            // แทนที่ form ด้วยข้อความสำเร็จ + ปุ่มส่งอีกครั้ง
            var container = form.closest('.wp-block-group') || form.parentElement;
            container.innerHTML = ''
                + '<div style="text-align:center;padding:30px;">'
                + '  <div style="font-size:48px;margin-bottom:16px;">📧</div>'
                + '  <h3 style="margin-bottom:8px;">ส่งลิงก์รีเซ็ตรหัสผ่านแล้ว!</h3>'
                + '  <p style="color:#666;margin-bottom:4px;">กรุณาตรวจสอบอีเมลของคุณที่</p>'
                + '  <p style="font-weight:600;color:#333;margin-bottom:20px;">' + email + '</p>'
                + '  <p style="color:#999;font-size:13px;margin-bottom:20px;">ลิงก์จะหมดอายุใน 1 ชั่วโมง<br>หากไม่ได้รับอีเมล กรุณาตรวจสอบโฟลเดอร์สแปม</p>'
                + '  <button id="fund-resend-btn" style="background:#667eea;color:white;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;">ส่งอีกครั้ง</button>'
                + '  <div id="fund-resend-timer" style="color:#999;font-size:13px;margin-top:8px;"></div>'
                + '  <div style="margin-top:20px;">'
                + '    <a href="/'+encodeURIComponent('เข้าสู่ระบบ')+'/" style="color:#667eea;text-decoration:none;">← กลับไปหน้าเข้าสู่ระบบ</a>'
                + '  </div>'
                + '</div>';

            // Resend with cooldown
            var resendBtn = document.getElementById('fund-resend-btn');
            var timerEl = document.getElementById('fund-resend-timer');
            var cooldown = 60;

            function startCooldown(){
                resendBtn.disabled = true;
                resendBtn.style.opacity = '0.5';
                var interval = setInterval(function(){
                    cooldown--;
                    timerEl.textContent = 'ส่งอีกครั้งได้ใน ' + cooldown + ' วินาที';
                    if(cooldown <= 0){
                        clearInterval(interval);
                        resendBtn.disabled = false;
                        resendBtn.style.opacity = '';
                        timerEl.textContent = '';
                    }
                }, 1000);
            }
            startCooldown();

            resendBtn.addEventListener('click', function(){
                if(resendBtn.disabled) return;
                jQuery.post(AJAX, {action:'fund_forgot', email:email}, function(){
                    msg('ส่งลิงก์ใหม่แล้ว! กรุณาตรวจสอบอีเมล', true);
                    cooldown = 60;
                    startCooldown();
                });
            });
        }

        btns.forEach(function(b){
            b.setAttribute('href','javascript:void(0)');
            b.addEventListener('click', doIt, true);
        });
        form.addEventListener('submit', doIt, true);
        emlInp.addEventListener('keydown', function(e){ if(e.key==='Enter') doIt(e); });

        log('FORGOT PASSWORD READY');
    }


    // ================================================================
    // RESET PASSWORD PAGE (เปิดจาก link ใน email)
    // ================================================================
    function initResetPassword(){
        // ดึง token จาก URL
        var params = new URLSearchParams(window.location.search);
        var token = params.get('token');

        if(!token){
            log('No reset token in URL');
            // แสดงข้อความว่าลิงก์ไม่ถูกต้อง
            var container = document.querySelector('.entry-content, .wp-block-group, main');
            if(container){
                container.innerHTML = ''
                    + '<div style="text-align:center;padding:40px;">'
                    + '  <div style="font-size:48px;margin-bottom:16px;">⚠️</div>'
                    + '  <h3>ลิงก์ไม่ถูกต้องหรือหมดอายุ</h3>'
                    + '  <p style="color:#666;">กรุณาขอลิงก์รีเซ็ตรหัสผ่านใหม่</p>'
                    + '  <a href="/forgot-password/" style="display:inline-block;margin-top:16px;background:#667eea;color:white;padding:10px 24px;border-radius:8px;text-decoration:none;">ขอลิงก์ใหม่</a>'
                    + '</div>';
            }
            return;
        }

        log('Reset token found: ' + token.substring(0,8) + '...');

        var form = document.querySelector('form[class*="gsbp-"]');
        if(!form){ log('No reset form'); return; }

        // จับ input ทุกตัวใน form
        var allInputs = form.querySelectorAll('input');
        var pwd = null, pwd2 = null;

        allInputs.forEach(function(inp, idx){
            var p = (inp.placeholder||'').toLowerCase();
            var n = (inp.name||'').toLowerCase();
            log('Reset input['+idx+']: name='+n+' type='+inp.type+' placeholder='+inp.placeholder);

            if(p.includes('ยืนยัน') || p.includes('confirm') || p.includes('อีกครั้ง')){
                pwd2 = inp;
            } else if(inp.type==='password' || n==='password' || p.includes('รหัสผ่าน') || p.includes('password')){
                if(!pwd) pwd = inp; else if(!pwd2) pwd2 = inp;
            }
        });

        // ถ้ามี input 2 ตัว type=password → ตัวแรก=password, ตัวสอง=confirm
        if(!pwd && allInputs.length >= 1) pwd = allInputs[0];
        if(!pwd2 && allInputs.length >= 2) pwd2 = allInputs[1];

        if(!pwd){ log('No password input'); return; }
        log('Reset fields: pwd='+pwd.placeholder+' pwd2='+(pwd2?pwd2.placeholder:'none'));

        // หาปุ่ม
        var btns = [];
        document.querySelectorAll('a, button').forEach(function(el){
            var t=(el.textContent||'').trim();
            var href = el.getAttribute('href')||'';
            if((t.indexOf('บันทึก')!==-1 || t.indexOf('รีเซ็ต')!==-1 || t.indexOf('เปลี่ยน')!==-1)
               && (href==='#'||href===''||href.indexOf('javascript:')===0)){
                btns.push(el);
            }
        });
        log('Found '+btns.length+' reset buttons');

        function doIt(e){
            if(e){ e.preventDefault(); e.stopImmediatePropagation(); }
            if(busy) return;
            log('Reset button clicked!');

            var pass = pwd.value;
            var pass2 = pwd2 ? pwd2.value : pass;

            if(!pass){ msg('กรุณากรอกรหัสผ่านใหม่',false); return; }
            if(pass.length<6){ msg('รหัสผ่านต้องมีอย่างน้อย 6 ตัว',false); return; }
            if(pass!==pass2){ msg('รหัสผ่านไม่ตรงกัน',false); return; }

            busy = true;
            btns.forEach(function(b){ b.style.opacity='0.5'; b.style.pointerEvents='none'; });

            jQuery.ajax({
                url:AJAX, method:'POST', timeout:20000,
                data:{action:'fund_reset_pw', token:token, password:pass},
                success:function(res){
                    log('Reset res: '+JSON.stringify(res).substring(0,200));
                    if(res.success && !res.data.error){
                        msg('เปลี่ยนรหัสผ่านสำเร็จ!', true);
                        setTimeout(function(){
                            safeRedirect('/'+encodeURIComponent('เข้าสู่ระบบ')+'/');
                        }, 1500);
                    } else {
                        var m = 'ลิงก์หมดอายุหรือไม่ถูกต้อง กรุณาขอลิงก์ใหม่';
                        var d = res.data||{};
                        if(d.error) m = d.error;
                        if(d.detail) m = d.detail;
                        msg(m, false);
                        busy=false;
                        btns.forEach(function(b){ b.style.opacity=''; b.style.pointerEvents=''; });
                    }
                },
                error:function(){
                    msg('เชื่อมต่อไม่ได้',false);
                    busy=false;
                    btns.forEach(function(b){ b.style.opacity=''; b.style.pointerEvents=''; });
                }
            });
        }

        btns.forEach(function(b){
            b.setAttribute('href','javascript:void(0)');
            b.addEventListener('click', doIt, true);
        });
        form.addEventListener('submit', doIt, true);
        allInputs.forEach(function(i){ i.addEventListener('keydown',function(e){ if(e.key==='Enter') doIt(e); }); });

        log('RESET PASSWORD READY');
    }


    // ================================================================
    // LOGOUT
    // ================================================================
    function doLogout(){
        jQuery.post(AJAX, {action:'fund_logout'}, function(){
            document.cookie = 'auth_api_token=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT';
            localStorage.removeItem('auth_user');
            msg('ออกจากระบบแล้ว', true);
            setTimeout(function(){ window.location.href='/'; }, 1000);
        });
    }


    // ================================================================
    // INIT
    // ================================================================
    // Redirect loop protection
    var RKEY = 'fund_redirect_count';
    var RTIME = 'fund_redirect_time';
    function safeRedirect(url){
        var now = Date.now();
        var lastTime = parseInt(sessionStorage.getItem(RTIME)||'0');
        var count = parseInt(sessionStorage.getItem(RKEY)||'0');
        // Reset counter ถ้าผ่านไป 10 วิ
        if(now - lastTime > 10000){ count = 0; }
        count++;
        sessionStorage.setItem(RKEY, count);
        sessionStorage.setItem(RTIME, now);
        if(count > 3){
            log('Redirect loop detected! Stopping.');
            sessionStorage.removeItem(RKEY);
            sessionStorage.removeItem(RTIME);
            return; // หยุด ไม่ redirect
        }
        window.location.href = url;
    }

    function go(){
        var p = decodeURIComponent(location.pathname);
        log('Page: ' + p);

        // ทุกหน้า: เช็ค login แล้วแสดง user menu ใน navbar
        initNavbar();

        // หน้าเฉพาะ
        if(p.indexOf('เข้าสู่ระบบ')!==-1 || p.indexOf('login')!==-1){
            initLogin();
        } else if(p.indexOf('สมัครสมาชิก')!==-1 || p.indexOf('register')!==-1){
            initRegister();
        } else if(p.indexOf('โปรไฟล์')!==-1 || p.indexOf('profile')!==-1){
            initProfile();
        } else if(p.indexOf('forgot-password')!==-1 || p.indexOf('ลืมรหัสผ่าน')!==-1){
            initForgotPassword();
        } else if(p.indexOf('reset-password')!==-1 || p.indexOf('รีเซ็ต')!==-1){
            initResetPassword();
        }
    }

    // รัน
    var started = false;
    function tryGo(){
        if(started) return;
        if(typeof jQuery === 'undefined'){
            log('Waiting for jQuery...');
            setTimeout(tryGo, 200);
            return;
        }
        started = true;
        go();
    }
    if(document.readyState==='loading'){
        document.addEventListener('DOMContentLoaded', function(){ setTimeout(tryGo,500); });
    } else {
        setTimeout(tryGo, 300);
    }
    setTimeout(tryGo, 2000);
    setTimeout(tryGo, 4000);

})();
</script>
    <?php
}