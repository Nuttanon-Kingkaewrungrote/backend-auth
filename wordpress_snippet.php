<?php
/**
 * WordPress Integration Snippet
 * 
 * วิธีใช้:
 * 1. ติดตั้ง Plugin "Code Snippets" ใน WordPress
 * 2. Snippets → Add New
 * 3. Copy โค้ดทั้งหมดนี้ไปวาง
 * 4. เปลี่ยน BACKEND_URL เป็น IP จริงของ VM
 * 5. Save and Activate
 */

// ⚠️ เปลี่ยน URL นี้ให้ตรงกับ VM จริง
define('BACKEND_URL', 'http://YOUR_VM_IP:8000');

// AJAX Handler - รับ Login จาก WordPress แล้วส่งไป Backend
add_action('wp_ajax_nopriv_fund_login', 'fund_login_handler');
add_action('wp_ajax_fund_login', 'fund_login_handler');

function fund_login_handler() {
    $username = sanitize_text_field($_POST['username']);
    $password = $_POST['password'];

    $response = wp_remote_post(BACKEND_URL . '/api/auth/login', array(
        'headers' => array('Content-Type' => 'application/json'),
        'body'    => json_encode(array(
            'username'    => $username,
            'password'    => $password,
            'remember_me' => false,
        )),
        'timeout' => 15,
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array(
            'message' => 'เชื่อมต่อ Backend ไม่ได้: ' . $response->get_error_message()
        ));
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    $body = json_decode(wp_remote_retrieve_body($response), true);

    if ($code === 200 && isset($body['token'])) {
        setcookie('auth_api_token', $body['token'], time() + 86400, '/', '', false, false);
        wp_send_json_success($body);
    } else {
        wp_send_json_error($body);
    }
}

// JavaScript - ดักจับ Login Form แล้วเรียก AJAX
add_action('wp_head', function() { ?>
<script>
(function() {
    function attachLoginHandler() {
        var $form = jQuery('form:has(input[name="password"])').first();
        if ($form.length === 0) return false;

        $form.off('submit.fundlogin').on('submit.fundlogin', function(e) {
            e.preventDefault();

            var username = jQuery(this).find('input[type="email"], input[type="text"]').first().val();
            var password = jQuery(this).find('input[name="password"]').val();
            var $btn     = jQuery(this).find('button[type="submit"], input[type="submit"]');

            if (!username || !password) {
                alert('กรุณากรอกอีเมลและรหัสผ่าน');
                return;
            }

            var originalText = $btn.text() || $btn.val();
            $btn.prop('disabled', true).text('กำลังเข้าสู่ระบบ...');

            jQuery.post('<?php echo esc_url(admin_url("admin-ajax.php")); ?>', {
                action:   'fund_login',
                username: username,
                password: password,
            }, function(res) {
                if (res.success) {
                    alert('✅ เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับ ' + res.data.user.username);
                    window.location.href = '/';
                } else {
                    var msg = (res.data && res.data.detail) ? res.data.detail : 'อีเมลหรือรหัสผ่านไม่ถูกต้อง';
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

    var observer = new MutationObserver(function() {
        if (attachLoginHandler()) observer.disconnect();
    });

    document.addEventListener('DOMContentLoaded', function() {
        if (!attachLoginHandler()) {
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });
})();
</script>
<?php }, 999);