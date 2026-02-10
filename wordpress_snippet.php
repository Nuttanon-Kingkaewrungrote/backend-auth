<?php
/**
 * WordPress Integration Snippet
 * Fund Dashboard - Backend API Connection
 * 
 * วิธีใช้:
 * 1. ติดตั้ง Plugin "Code Snippets" ใน WordPress
 * 2. Snippets → Add New
 * 3. Copy โค้ดทั้งหมดนี้ไปวาง
 * 4. เปลี่ยน BACKEND_URL เป็น IP จริงของ VM
 * 5. Location → Run everywhere
 * 6. Save and Activate
 */

// ⚠️ เปลี่ยน URL นี้ให้ตรงกับ VM จริง
define('BACKEND_URL', 'http://YOUR_VM_IP:8000');


// ============================================================
// 1. LOGIN HANDLER
// ============================================================
add_action('wp_ajax_nopriv_fund_login', 'fund_login_handler');
add_action('wp_ajax_fund_login', 'fund_login_handler');

function fund_login_handler() {
    $username = sanitize_text_field($_POST['username']);
    $password = $_POST['password'];
    $remember = isset($_POST['remember']) ? true : false;

    $response = wp_remote_post(BACKEND_URL . '/api/auth/login', array(
        'headers' => array('Content-Type' => 'application/json'),
        'body'    => json_encode(array(
            'username'    => $username,
            'password'    => $password,
            'remember_me' => $remember,
        )),
        'timeout' => 15,
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'เชื่อมต่อ Backend ไม่ได้: ' . $response->get_error_message()));
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);

    if ($code === 200 && isset($body['token'])) {
        $expire = $remember ? time() + (30 * 24 * 60 * 60) : time() + 86400;
        setcookie('auth_api_token', $body['token'], $expire, '/', '', false, false);
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}


// ============================================================
// 2. REGISTER HANDLER
// ============================================================
add_action('wp_ajax_nopriv_fund_register', 'fund_register_handler');
add_action('wp_ajax_fund_register', 'fund_register_handler');

function fund_register_handler() {
    $username = sanitize_text_field($_POST['username']);
    $email    = sanitize_email($_POST['email']);
    $password = $_POST['password'];

    if (empty($username) || empty($password)) {
        wp_send_json_error(array('message' => 'กรุณากรอก Username และ Password'));
        return;
    }

    $response = wp_remote_post(BACKEND_URL . '/api/auth/register', array(
        'headers' => array('Content-Type' => 'application/json'),
        'body'    => json_encode(array(
            'username' => $username,
            'email'    => $email,
            'password' => $password,
        )),
        'timeout' => 15,
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'เชื่อมต่อ Backend ไม่ได้: ' . $response->get_error_message()));
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);

    if ($code === 200) {
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}


// ============================================================
// 3. LOGOUT HANDLER
// ============================================================
add_action('wp_ajax_fund_logout', 'fund_logout_handler');

function fund_logout_handler() {
    // ลบ Cookie
    setcookie('auth_api_token', '', time() - 3600, '/', '', false, false);
    wp_send_json_success(array('message' => 'ออกจากระบบสำเร็จ'));
}


// ============================================================
// 4. VERIFY TOKEN HANDLER (เช็คว่า Login อยู่หรือไม่)
// ============================================================
add_action('wp_ajax_fund_verify', 'fund_verify_handler');
add_action('wp_ajax_nopriv_fund_verify', 'fund_verify_handler');

function fund_verify_handler() {
    $token = isset($_POST['token']) ? $_POST['token'] : '';

    if (empty($token)) {
        wp_send_json_error(array('message' => 'No token provided'));
        return;
    }

    $response = wp_remote_get(BACKEND_URL . '/api/auth/verify', array(
        'headers' => array(
            'Authorization' => 'Bearer ' . $token,
            'Content-Type'  => 'application/json',
        ),
        'timeout' => 15,
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => 'เชื่อมต่อ Backend ไม่ได้'));
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);

    if ($code === 200) {
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}


// ============================================================
// 5. JAVASCRIPT - ดักจับ Form อัตโนมัติ
// ============================================================
add_action('wp_head', function() { ?>
<script>
(function() {

    // ---------- UTILS ----------
    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }

    function deleteCookie(name) {
        document.cookie = name + '=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }

    var ajaxUrl = '<?php echo esc_url(admin_url("admin-ajax.php")); ?>';


    // ---------- LOGIN FORM ----------
    function attachLoginHandler() {
        var $form = jQuery('form:has(input[name="password"])').first();
        if ($form.length === 0) return false;

        // เช็คว่าไม่ใช่ register form
        var hasUsername = $form.find('input[name="username"], input[name="email"]').length > 0;
        var hasConfirm  = $form.find('input[name="confirm_password"], input[name="password_confirm"]').length > 0;
        if (!hasUsername || hasConfirm) return false;

        $form.off('submit.fundlogin').on('submit.fundlogin', function(e) {
            e.preventDefault();

            var username = jQuery(this).find('input[type="email"], input[type="text"]').first().val();
            var password = jQuery(this).find('input[name="password"]').val();
            var remember = jQuery(this).find('input[name="remember"], input[type="checkbox"]').is(':checked');
            var $btn     = jQuery(this).find('button[type="submit"], input[type="submit"]');

            if (!username || !password) {
                alert('กรุณากรอกอีเมลและรหัสผ่าน');
                return;
            }

            var originalText = $btn.text() || $btn.val();
            $btn.prop('disabled', true).text('กำลังเข้าสู่ระบบ...');

            jQuery.post(ajaxUrl, {
                action:   'fund_login',
                username: username,
                password: password,
                remember: remember ? 1 : 0,
            }, function(res) {
                if (res.success) {
                    alert('✅ เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับ ' + res.data.user.username);
                    window.location.href = '/';
                } else {
                    var msg = (res.data && res.data.detail) ? res.data.detail :
                              (res.data && res.data.message) ? res.data.message :
                              'อีเมลหรือรหัสผ่านไม่ถูกต้อง';
                    alert('❌ ' + msg);
                    $btn.prop('disabled', false).text(originalText);
                }
            }).fail(function() {
                alert('❌ เกิดข้อผิดพลาด กรุณาลองใหม่');
                $btn.prop('disabled', false).text(originalText);
            });
        });

        return true;
    }


    // ---------- REGISTER FORM ----------
    function attachRegisterHandler() {
        // หา register form จาก confirm password หรือ name="email" + name="username"
        var $form = jQuery('form:has(input[name="confirm_password"]), form:has(input[name="password_confirm"])').first();
        if ($form.length === 0) return false;

        $form.off('submit.fundregister').on('submit.fundregister', function(e) {
            e.preventDefault();

            var username = jQuery(this).find('input[name="username"]').val();
            var email    = jQuery(this).find('input[name="email"]').val();
            var password = jQuery(this).find('input[name="password"]').val();
            var confirm  = jQuery(this).find('input[name="confirm_password"], input[name="password_confirm"]').val();
            var $btn     = jQuery(this).find('button[type="submit"], input[type="submit"]');

            if (!username || !password) {
                alert('กรุณากรอก Username และ Password');
                return;
            }

            if (password !== confirm) {
                alert('❌ รหัสผ่านไม่ตรงกัน');
                return;
            }

            if (password.length < 6) {
                alert('❌ รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร');
                return;
            }

            var originalText = $btn.text() || $btn.val();
            $btn.prop('disabled', true).text('กำลังสมัครสมาชิก...');

            jQuery.post(ajaxUrl, {
                action:   'fund_register',
                username: username,
                email:    email,
                password: password,
            }, function(res) {
                if (res.success) {
                    alert('✅ สมัครสมาชิกสำเร็จ! กรุณา Login');
                    window.location.href = '/เข้าสู่ระบบ/';
                } else {
                    var msg = (res.data && res.data.detail) ? res.data.detail :
                              (res.data && res.data.message) ? res.data.message :
                              'สมัครสมาชิกไม่สำเร็จ';
                    alert('❌ ' + msg);
                    $btn.prop('disabled', false).text(originalText);
                }
            }).fail(function() {
                alert('❌ เกิดข้อผิดพลาด กรุณาลองใหม่');
                $btn.prop('disabled', false).text(originalText);
            });
        });

        return true;
    }


    // ---------- LOGOUT BUTTON ----------
    function attachLogoutHandler() {
        jQuery(document).on('click', '.fund-logout, #fund-logout, [data-action="logout"]', function(e) {
            e.preventDefault();
            if (!confirm('คุณต้องการออกจากระบบหรือไม่?')) return;

            jQuery.post(ajaxUrl, {
                action: 'fund_logout',
            }, function(res) {
                deleteCookie('auth_api_token');
                localStorage.removeItem('auth_user');
                alert('ออกจากระบบแล้ว');
                window.location.href = '/';
            });
        });
    }


    // ---------- AUTO SHOW USER STATUS ----------
    function showUserStatus() {
        var token = getCookie('auth_api_token');
        if (!token) return;

        jQuery.post(ajaxUrl, {
            action: 'fund_verify',
            token:  token,
        }, function(res) {
            if (res.success && res.data.user) {
                var user = res.data.user;
                localStorage.setItem('auth_user', JSON.stringify(user));

                // แสดงชื่อ user (ปรับ selector ตาม theme)
                var html = '<span class="fund-user-greeting">สวัสดี <strong>' + user.username + '</strong></span> ' +
                           '<a href="#" class="fund-logout" style="color:#dc3545;margin-left:10px;">ออกจากระบบ</a>';

                jQuery('.fund-user-status').html(html);
                jQuery('.fund-login-btn').hide();
                jQuery('.fund-logout-btn').show();
            } else {
                // Token หมดอายุ
                deleteCookie('auth_api_token');
                localStorage.removeItem('auth_user');
            }
        });
    }


    // ---------- INIT - รอ DOM โหลดเสร็จ ----------
    var observer = new MutationObserver(function() {
        attachLoginHandler();
        attachRegisterHandler();
    });

    document.addEventListener('DOMContentLoaded', function() {
        attachLoginHandler();
        attachRegisterHandler();
        attachLogoutHandler();
        showUserStatus();

        // Observer สำหรับ Dynamic content
        observer.observe(document.body, { childList: true, subtree: true });
    });

})();
</script>
<?php }, 999);