<?php

namespace App\Framework;

abstract class Model
{
    protected static $listeners = [];
    protected static $scopes = [];

    public static function boot()
    {
        foreach (class_uses_recursive(static::class) as $trait) {
            $method = '__boot_' . basename(str_replace('\\', '/', $trait));
            if (method_exists(static::class, $method)) {
                forward_static_call([static::class, $method]);
            }
        }
    }

    public static function saving($callback) { static::$listeners['saving'][] = $callback; }
    public static function saved($callback) { static::$listeners['saved'][] = $callback; }
    public static function creating($callback) { static::$listeners['creating'][] = $callback; }
    public static function deleting($callback) { static::$listeners['deleting'][] = $callback; }
    public static function addGlobalScope($name, $callback) { static::$scopes[$name] = $callback; }
}
