<?php
// api-proxy.php - скрипт прокси на PHP
error_reporting(E_ALL);
ini_set('display_errors', 0);

$path = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];

// Обработка локального orph.php
if (strpos($path, '/orph.php') === 0 || strpos($path, '/orph') === 0) {
    // Включаем локальный файл orph.php
    include __DIR__ . '/orph.php';
    exit;
}

// Определить целевой URL
$target_url = '';
$content_type = 'application/json; charset=utf-8';
$api_base = getenv('RUEO_API_URL') ?: 'http://localhost:8000';

$proxied_paths = [
    '/search',
    '/suggest',
    '/status/info',
    '/admin/import',
    '/admin/import/status',
];

foreach ($proxied_paths as $prefix) {
    if (strpos($path, $prefix) === 0) {
        $query = $_SERVER['QUERY_STRING'] ?? '';
        $target_url = rtrim($api_base, '/') . $path . ($query ? '?' . $query : '');
        break;
    }
}

if ($target_url) {
    // Выполнить прокси-запрос
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $target_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (compatible; Rueo Proxy)');
    curl_setopt($ch, CURLOPT_ENCODING, ''); // Принимать любой тип сжатия
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    // Передать заголовки
    $headers = [];
    foreach (getallheaders() as $key => $value) {
        if (strtolower($key) !== 'host' && strtolower($key) !== 'accept-encoding') {
            $headers[] = $key . ': ' . $value;
        }
    }
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    
    if ($method !== 'GET') {
        $payload = file_get_contents('php://input');
        if ($payload !== false) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        }
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    }

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $content_type_header = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    curl_close($ch);
    
    // Вернуть ответ с правильными заголовками
    http_response_code($http_code);
    
    // Использовать Content-Type от оригинального сервера, если он есть
    if ($content_type_header) {
        header('Content-Type: ' . $content_type_header);
    } else {
        header('Content-Type: ' . $content_type);
    }
    
    // Добавить заголовки для предотвращения кэширования прокси
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');
    
    echo $response;
} else {
    http_response_code(404);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => 'API endpoint not found']);
}
?>
