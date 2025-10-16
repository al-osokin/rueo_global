<?php
// Единый, надежный SMTP скрипт с детальным логированием

function utf8_base64($text) {
	return '=?UTF-8?B?' . base64_encode($text) . '?=';
}

function log_message($url, $error_text, $comment) {
	$log_file = __DIR__ . '/logs/orph.txt';
	$date = date('d.m.y');
	$log_entry = $date . "\n" .
				 "Адрес: " . $url . "\n" .
				 "Ошибка: " . $error_text . "\n" .
				 "Комментарий: " . $comment . "\n\n";
	file_put_contents($log_file, $log_entry, FILE_APPEND | LOCK_EX);
}

// --- НОВЫЙ SMTP КЛИЕНТ ---

function smtp_send($to, $subject, $body) {
	global $smtp_config;
	if (!file_exists(__DIR__ . '/.smtp_config.php')) {
		log_smtp("SMTP ERROR: .smtp_config.php not found.");
		return false;
	}
	include __DIR__ . '/.smtp_config.php';

	if (!empty($smtp_config['debug'])) {
		$log_file = __DIR__ . '/logs/mail_errors.log';
		// Очищаем лог для новой попытки, чтобы было чисто
		file_put_contents($log_file, "--- NEW SMTP ATTEMPT AT " . date('Y-m-d H:i:s') . " ---\n", FILE_APPEND | LOCK_EX);
		file_put_contents($log_file, "To: $to, Subject: $subject\n", FILE_APPEND | LOCK_EX);
		file_put_contents($log_file, "Connecting to " . $smtp_config['host'] . ":" . $smtp_config['port'] . "\n", FILE_APPEND | LOCK_EX);
	}

	$connection = stream_socket_client($smtp_config['host'] . ':' . $smtp_config['port'], $errno, $errstr, 30);
	if (!$connection) {
		log_smtp("Connection failed: $errstr ($errno)");
		return false;
	}
	stream_set_timeout($connection, 15); // Таймаут 15 секунд
	log_smtp_response($connection); // 220 Welcome

	// EHLO
	if (smtp_command($connection, "EHLO " . $smtp_config['host'], 250) === false) {
		fclose($connection);
		return false;
	}

	// STARTTLS
	if (smtp_command($connection, "STARTTLS", 220) === false) {
		fclose($connection);
		return false;
	}
	if (!stream_socket_enable_crypto($connection, true, STREAM_CRYPTO_METHOD_TLSv1_2_CLIENT)) {
		log_smtp("Failed to enable TLS");
		fclose($connection);
		return false;
	}
	log_smtp("TLS enabled successfully.");

	// EHLO again after TLS
	if (smtp_command($connection, "EHLO " . $smtp_config['host'], 250) === false) {
		fclose($connection);
		return false;
	}

	// AUTH LOGIN
	if (smtp_command($connection, "AUTH LOGIN", 334) === false) {
		fclose($connection);
		return false;
	}
	if (smtp_command($connection, base64_encode($smtp_config['username']), 334) === false) {
		fclose($connection);
		return false;
	}
	if (smtp_command($connection, base64_encode($smtp_config['password']), 235) === false) {
		fclose($connection);
		return false;
	}

	// MAIL FROM
	if (smtp_command($connection, "MAIL FROM:<" . $smtp_config['from'] . ">", 250) === false) {
		fclose($connection);
		return false;
	}

	// RCPT TO
	if (smtp_command($connection, "RCPT TO:<$to>", 250) === false) {
		fclose($connection);
		return false;
	}

	// DATA
	if (smtp_command($connection, "DATA", 354) === false) {
		fclose($connection);
		return false;
	}

	// Email Body
	$headers = "From: " . utf8_base64($smtp_config['from_name']) . " <" . $smtp_config['from'] . ">\r\n";
	$headers .= "To: <$to>\r\n";
	$headers .= "Subject: " . utf8_base64($subject) . "\r\n";
	$headers .= "Content-Type: text/plain; charset=utf-8\r\n";
	$headers .= "Content-Transfer-Encoding: 8bit\r\n";
	$message = $headers . "\r\n" . $body;
	if (smtp_command($connection, $message . "\r\n.", 250) === false) {
		fclose($connection);
		return false;
	}

	// QUIT
	smtp_command($connection, "QUIT", 221);
	fclose($connection);

	log_smtp("SMTP session finished successfully.");
	return true;
}

function smtp_command($socket, $command, $expected_code = null) {
	log_smtp("C: " . $command);
	fwrite($socket, $command . "\r\n");
	$response = log_smtp_response($socket);
	
	// Проверка кода ответа, если указан ожидаемый код
	if ($expected_code !== null) {
		$code = intval(substr($response, 0, 3));
		if ($code !== $expected_code && !in_array($code, (array)$expected_code)) {
			log_smtp("ERROR: Expected code " . (is_array($expected_code) ? implode('/', $expected_code) : $expected_code) . " but got $code");
			return false;
		}
	}
	
	return $response;
}

function log_smtp_response($socket) {
	$response = '';
	while (substr($response, 3, 1) != ' ') {
		if (!($line = fgets($socket, 512))) {
			break;
		}
		$response .= $line;
	}
	log_smtp("S: " . trim($response));
	return $response;
}

function log_smtp($message) {
    // Всегда пишем в лог, независимо от настройки debug
    if (!file_exists(__DIR__ . '/logs')) {
        mkdir(__DIR__ . '/logs', 0755, true);
    }
    file_put_contents(__DIR__ . '/logs/mail_errors.log', $message . "\n", FILE_APPEND | LOCK_EX);
}


// --- ОСНОВНАЯ ЛОГИКА ---

if (isset($_POST['key']) && $_POST['key']=='2З5'):
    $url = isset($_POST['url']) ? trim(strip_tags($_POST['url'])) : '';
    $error_text = isset($_POST['text']) ? trim(strip_tags($_POST['text'])) : '';
    $comment = isset($_POST['comment']) ? trim(strip_tags($_POST['comment'])) . "\n" : '';

    if (empty($url) || empty($error_text)) {
        header('HTTP/1.0 400 Bad Request');
        echo 'Mankas datumoj';
        exit;
    }

    $body = "Адрес: " . $url . "\n";
    $body .= "Ошибка: " . $error_text . "\n";
    $body .= "Комментарий: " . $comment . "\n";

    log_message($url, $error_text, $comment);

    $subject = 'Орфографическая ошибка';
    if (preg_match('#/sercxo/(.*)#', $url, $matches)) {
        $subject = urldecode($matches[1]) . ': орфографическая ошибка';
    }

    // Продолжаем выполнение даже если клиент отключился
    ignore_user_abort(true);
    set_time_limit(60);
    
    // Возвращаем успех сразу
    echo 'Bone';
    
    // Пытаемся закрыть соединение с клиентом
    if (function_exists('fastcgi_finish_request')) {
        fastcgi_finish_request();
    } else {
        // Для других серверов включая встроенный PHP
        header('Content-Length: ' . ob_get_length());
        header('Connection: close');
        ob_end_flush();
        ob_flush();
        flush();
    }
    
    // Отправляем письмо в фоне
    smtp_send('vortaristo@a-v-o.ru', $subject, $body);
else:
?>
<!-- HTML-форма остается без изменений -->
<div class="modal fade" id="orph" tabindex="-1" role="dialog" aria-hidden="true">
<form action="/orph.php" method="post">
<div class="modal-dialog" role="document">
<div class="modal-content">
<div class="modal-header">
<h5 class="modal-title">Отправить сообщение об ошибке</h5>
<button type="button" class="close" data-dismiss="modal" aria-label="Close">
<span aria-hidden="true">&times;</span>
</button>
</div>
<div class="modal-body text-left">
<div class="form-group">
<label for="orph-url">Страница:</label>
<input type="text" class="form-control" id="orph-url" name="url"/>
</div>
<div class="form-group">
<label for="orph-text">Ошибка в тексте:</label>
<input type="text" class="form-control" id="orph-text" name="text"/>
</div>
<div class="form-group">
<label for="orph-comment">Комментарий (не обязательно):</label>
<input type="text" class="form-control" id="orph-comment" name="comment"/>
</div>
<div class="text-muted">Вы останетесь на этой же странице</div>
<div class="alert alert-danger mt-3" style="display:none;"></div>
<div class="alert alert-success mt-3" style="display:none;"></div>
</div>
<div class="modal-footer">
<button type="button" class="btn btn-secondary" data-dismiss="modal">Закрыть</button>
<button type="submit" class="btn btn-primary">Отправить</button>
</div>
</div>
</div>
</form>
</div>

<script type="text/javascript">
$(function() {
	$(document).keydown(function(e) {
        if (e.ctrlKey && e.keyCode == 13) {
            orph();
        }
    });
    $('#orph form').submit(function() {
        orph_send();
        return false;
    });
});
function orph() {
    var $form = $('#orph form');
    $form.append('<input type="hidden" name="key" value="2З5">');
    $('#orph-url').val(window.location.href);
    var sel = '';
    if (window.getSelection) {
		sel = window.getSelection().toString();
	} else if (document.selection) {
		sel = document.selection.createRange().text;
	}
    $('#orph-text').val(sel);
    $form.find('button[type=submit]').show();
    $form.find('.alert-danger').hide();
    $form.find('.alert-success').hide();
    $('#orph').modal();
}
function orph_send() {
    var $form = $('#orph form');
    if ($form.find('alert-success').is(':visible')) {
        $form.find('alert-success').hide();
        $('#orph').modal('hide');
    } else {
        $.ajax({
            url: $form.attr('action'),
            type: $form.attr('method'),
            data: $form.serialize(),
            success: function() {
                $form.find('.alert-danger').hide();
                $form.find('button[type=submit]').hide();
                $form.find('.alert-success').text('Сообщение отправлено').fadeIn();
            },
            error: function() {
                $form.find('.alert-danger').text('Ошибка отправки').fadeIn();
            }
        });
    }
}
</script>
<?php
endif;
?>
