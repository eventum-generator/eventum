# Structured logging data model

## Common

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>count</td>
        <td>Number of elements</td>
        <td>int</td>
    </tr>
    <tr>
        <td>reason</td>
        <td>Reason of event (e.g. exception message)</td>
        <td>str</td>
    </tr>
    <tr>
        <td>parameters</td>
        <td>Complex parameters or configuration dictionary</td>
        <td>dict</td>
    </tr>
    <tr>
        <td>value</td>
        <td>Specific value related to event message</td>
        <td>Any</td>
    </tr>
    <tr>
        <td>hint</td>
        <td>Actionable suggestion for resolving the issue</td>
        <td>str</td>
    </tr>
    <tr>
        <td>timeout</td>
        <td>Timeout in seconds</td>
        <td>int</td>
    </tr>

</table>

## Python

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>package_name</td>
        <td>Name of the package</td>
        <td>str</td>
    </tr>
    <tr>
        <td>module_name</td>
        <td>Name of the module</td>
        <td>str</td>
    </tr>
    <tr>
        <td>traceback</td>
        <td>Formatted traceback</td>
        <td>str</td>
    </tr>
</table>

## Asynchrony

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>task_name</td>
        <td>Name of the task</td>
        <td>str</td>
    </tr>
</table>

## Network

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>host</td>
        <td>Network address (ip or hostname)</td>
        <td>str</td>
    </tr>
    <tr>
        <td>port</td>
        <td>Port number</td>
        <td>int</td>
    </tr>
    <tr>
        <td>url</td>
        <td>URL address</td>
        <td>str</td>
    </tr>
    <tr>
        <td>http_status</td>
        <td>HTTP response code</td>
        <td>int</td>
    </tr>
</table>

## File system

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>file_path</td>
        <td>Path to file</td>
        <td>str</td>
    </tr>
    <tr>
        <td>path</td>
        <td>Directory path</td>
        <td>str</td>
    </tr>
</table>

## Time

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>seconds</td>
        <td>Duration in seconds</td>
        <td>float</td>
    </tr>
</table>

## Threads and Processes

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>process_id</td>
        <td>ID of the process</td>
        <td>int</td>
    </tr>
    <tr>
        <td>thread_id</td>
        <td>ID of the thread</td>
        <td>int</td>
    </tr>
</table>

## OS

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>signal</td>
        <td>Name of the signal</td>
        <td>str</td>
    </tr>
</table>

## App

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>generator_id</td>
        <td>ID of the generator</td>
        <td>str</td>
    </tr>
    <tr>
        <td>generator_ids</td>
        <td>ID of generators</td>
        <td>list[str]</td>
    </tr>
    <tr>
        <td>running_generators</td>
        <td>IDs of running generators</td>
        <td>list[str]</td>
    </tr>
    <tr>
        <td>non_running_generators</td>
        <td>IDs of non running generators</td>
        <td>list[str]</td>
    </tr>
</table>

## Plugins

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>plugin_type</td>
        <td>Type of plugin (e.g. "input", "event" etc.)</td>
        <td>str</td>
    </tr>
    <tr>
        <td>plugin_name</td>
        <td>Name of plugin (e.g. "cron")</td>
        <td>str</td>
    </tr>
    <tr>
        <td>plugin_id</td>
        <td>ID of plugin instance</td>
        <td>int</td>
    </tr>
    <tr>
        <td>plugin_class</td>
        <td>Class of the plugin (shown during registration process)</td>
        <td>str</td>
    </tr>
    <tr>
        <td>plugin_config_class</td>
        <td>Class of the plugin config (shown during registration process)</td>
        <td>str</td>
    </tr>
</table>

### Input plugins

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>start_timestamp</td>
        <td>Start timestamp of plugin generation in ISO8601 format</td>
        <td>str</td>
    </tr>
    <tr>
        <td>end_timestamp</td>
        <td>End timestamp of plugin generation in ISO8601 format</td>
        <td>str</td>
    </tr>
</table>

### Event plugins

#### Template Event plugin

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>template_alias</td>
        <td>Alias of template (used in generic context or when file_path is not known)</td>
        <td>str</td>
    </tr>
    <tr>
        <td>sample_alias</td>
        <td>Alias of sample (used in generic context or when file_path is not known)</td>
        <td>str</td>
    </tr>
</table>

### Output plugins

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>original_event</td>
        <td>Original event</td>
        <td>str</td>
    </tr>
</table>

## Security

<table>
    <th>Name</th>
    <th>Description</th>
    <th>Data type</th>
    <tr>
        <td>secret</td>
        <td>Name of the secret</td>
        <td>str</td>
    </tr>
</table>
