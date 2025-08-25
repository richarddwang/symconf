# TwinConf
An entanglement of configuration and code.

Table of contents:
- [Construct configuration](#construct-configuration)
    - [1. Read YAML and dotenv files](#1-read-yaml-and-dotenv-files)
    - [2. MERGE configuration](#2-merge-configuration)
    - [3. Command line arguments](#3-command-line-arguments)
    - [4. Remove argument value](#4-remove-argument-value)
    - [5. Default argument value of object](#5-default-argument-value-of-object)
    - [6. Variable Interpolation](#6-variable-interpolation)
    - [7. Expression Interpolation](#7-expression-interpolation)
- [Validation](#validation)
    - [Validate type](#validate-type)
    - [Check unexpected/missing arguments](#check-unexpectedmissing-arguments)
- [Identify object's arguments](#identify-objects-arguments)
- [Configuration Object](#configuration-object)
    - [Access & Manipulation](#access--manipulation)
    - [Serialization](#serialization)
    - [Resolve object](#resolve-object)
- [List manipulation](#list-manipulation)
- [Sweep over values](#sweep-over-values)

## Construct configuration

- Given: 入口程式初始化 `TwinConf` parser 並啟動它
    ```python
    # main.py
    parser = TwinConfParser(...)
    config = parser.parse_args()
    ```

執行時 TwinConf 會依序執行下列階段建構，最終得出設置 `config` 
1. 讀取 YAML 和 dotenv 檔案
2. MERGE 設置
3. 命令列參數
4. 物件初始化的參數預設值
5. Variable Interpolation
6. Expression Interpolation

### 1. Read YAML and dotenv files

- Given: 一或多個 YAML 檔案
    ```yaml
    server: 
        host: localhost
        ports: 
            - 8080
            - 8081
    ```
    ```yaml
    server:
        timeout: 10
        ports:
            - 9090
    ```
- And: 
    ```dotenv
    .env
    LOGGING_SERVER=wandb.com
    API_KEY=pk-123
    ```
    ```dotenv
    # .env2
    API_KEY=pk-321
    ```
- When: 執行入口 Python 腳本並附上 YAML 或 dotenv 檔案
    ```bash
    python main.py --config <yaml_file> --config <yaml_file> ... --env .<dotenv_file> --env <dotenv_fiel>...
    ```
- Then: 得到 `config` 等同
    ```yaml
    server:
        host: localhost
        timeout: 10
        ports:
            - 9090
    ```
    - 不同 YAML 的設置會被 nested merged，越後面的 YAML 檔越優先。
    - 注意 list 會被直接取代
- And: 匯入 dotenv 設定的環境參數，越後面的 dotenv 檔越優先


### 2. MERGE configuration

疊加 YAML 檔案雖然方便，但也可能造成難以理解參數間的覆寫關係。TwinConf 能在 YAML 裡直接引用別的 YAML 的設置。

- Given `TwinConfParser(config_lib="./configs")`
- And: 
    ```yaml
    # ./configs/servers/default.yaml
    server:
        timeout: 10
        port: 9090
    more_level:
        server2:
            port: 7070
            host: awesome.com
    ```
    ```yaml
    # config.yaml
    server:
        MERGE: servers.default.server
        host: localhost
        MERGE: servers.default.more_level.server2
        port: 8080
    ```
    MERGE 的值是相對於 `config_lib` 的檔案路徑，可以再後綴欲指涉的設置的鍵
- When: `python main.py --config config.yaml`
- Then: 得到 `config` 等同
    ```
    server:
        timeout: 10
        port: 8080
        host: awesome.com
    ```
    由上往下執行，因此後面的值在深度合併裡會覆寫前面的值

### 3. Command line arguments

- When: `python main.py --config=<yaml_file> --model.seed=3`
- Then: 無論 YAML 檔案最後設置如何，CLI 參數都會以更高的優先度複寫

### 4. Remove argument value

- Given `TwinConfParser(config_lib="./configs")`
- And: 
    ```yaml
    # ./configs/servers/default.yaml
    server:
        timeout: 10
        port: 9090
    ```
    ```yaml
    # config.yaml
    server:
        MERGE: servers.default.server
        timeout: DELETE
    ```
- When: `python main.py --config config.yaml`
- Then: 得到 `config` 等同
    ```
    server:
        port: 9090
    ```

### 5. Default argument value of object

當某設置是針對某物件，且該物件初始化的某參數使用者沒有設定時，且該物件初始化參數有預設值時，自動將設置中該參數設定為預設值。這樣保證了在記錄設置時的完整性，即使在之後物件參數的預設值改變，也不會導致無法使用之前記錄的設置複現。

- Given: 某設置是個物件
    ```yaml
    model:
        TYPE: awesome_package.model.AwesomeModel
        learning_rate: 1e-3
    ```
- And: 該物件的初始化有預設參數值
    ```python
    class AwesomeModel
        def __init__(self, learning_rate: float = 1e-4, batch_size=32):
    ```
- When: 讀取設置後
- Then: 得到設置等同於
    ```python
    {'model': 
        {
            'TYPE': awesome_package.model.AwesomeModel,
            'learning_rate': 1e-3,
            'batch_size': 32 
        }
    }
    ```

### 6. Variable Interpolation

如同 Python f-string 般的功能

- Given: YAML 檔如
    ```yaml
    model: 
        output_features: ${dataset.num_classes} 
    log:
        name: 'n=${dataset.num_classes}'
    dataset:
        num_classes: ${NUM_CLASSES}
    ```
    - 可以單獨使用變數，也可以將變數夾雜在字串裡
    - 可以指涉環境變數，若 TwinConf 無法在設置中找到該變數，就會從環境變數中找

- And: 環境變數 `NUM_CLASSES` 為 10
- When: 讀取該 YAML 檔設置
- Then: 等同於 placeholders 被替換成相應的值
    ```python
    {
        'model': {'output_features': 10},
        'log': {'name': 'n=10'} 
        'dataset': {'num_classes': 10},
    }
    ```
    在此例子中，TwinConf 會先嘗試解析 `dataset.num_clasess`，發現其也使用 variable interpolation，則會再解析 `NUM_CLASSES`
    
### 7. Expression Interpolation

- Given: YAML 檔如
    ```yaml
    dataset:
        num_classes: 10
    model: 
        output_features: ${`dataset.num_classes` + `model.extra_outputs`} 
        extra_outputs: 2
    ```
    使用 backquotes 包住參數，則 ${} 包住的是 Python 表達式

- When: 讀取該 YAML
- Then: 替換成表達式的結果。等同於
    ```yaml
    dataset:
        num_classes: 10
    model: 
        output_features: 12 
        extra_outputs: 2
    ```

## Validation

- Given:
    ```python
    class Parent:
        def __init__(
            self, 
            name: str,
            number: int | float = None, 
            vocab: None | list[float] = None,
            toy: Union[str, None] = None,
        ): ...
    
    class Child:
        def __init__(
            self, 
            percent: float, 
            animal: Literal['cat', 'dog'] = 'dog', 
            dummy = 3, 
            name: Optional[str] = None,
            toy: Toy = None,
            stoy: SuperToy = None,
            toy_cls: Type[Toy] = None,
            **kwargs
        ):
            super().__init__(name=name or "John", **kwargs)

    class Toy: ...

    class SuperToy(Toy): ...

    def square(value: float) -> float: ...
    ```

以下的每個檢查在 `TwinConfParser` 初始化時都可以選擇性關閉，預設為開啟

### Validate type

規則：
- 參數值必須符合其型別註解 
- 若參數無型別註解則不檢查
- 參數型別若是 container，則只檢查第一層的型別
- 若參數設為物件，則以該物件的返回值檢查是否符合參數型別
- 若參數設為物件且帶有標籤 `!!base_class:xxx`，則該物件的 `TYPE` 後的類別必須是屬於 `xxx` 類別（同類別或其子類別）

範例

- Given: 設置
    ```yaml
    model:
        TYPE: Child
        percent: 1 # 報錯。 應該要是 float
        animal: pig # 報錯。值應該是 'cat' 或 'dog'
        dummy: false # 不報錯。無型別註解不檢查
        toy: # 不報錯。其類別初始化的返回值屬於型別提示中的類別
            TYPE: SuperToy
        stoy: !!base_class:SuperToy
            TYPE: Toy # 報錯。Toy 不是 SuperToy 或其子類別
        toy_cls: !!python/name:__main__.Toy # 若要傳入類別的型別本身而非其實體，則可使用 pyyaml built-in tag
        number: # 不報錯。該函式的返回值屬於型別提示中的類別
            TYPE: square
            value: 0.3
        name: null # 不報錯。相同參數只看最子類別的定義
        vocab: [a, b] # 不報錯。因為當型別是 container 時只檢查第一層型別
    ```
- When: 讀取設置
- Then: 會一次性報所有的錯，且
    每行錯誤訊息會包含以下資訊：物件名、參數名、期待的型別、實際的型別、實際的參數值

### Check unexpected/missing arguments

- Given: 設置
    ```yaml
    model:
        TYPE: Child
        parcent: 0.1 # 報錯。不預期參數 parcent
        # 報錯， 預期要有 percent 參數
        # 不會報錯沒有 name 參數，因為 name 的定義是看最子類別 Child 的定義
    ```
- When: 讀取設置
- Then: 一次性報錯。每行錯誤訊息會包含以下資訊：物件名、參數名、錯誤類型(缺少/不預期)

## Identify object's arguments

安裝 `TwinConf` 會附帶一個 bash command `twinhelp`，它可以協助你了解 `TwinConf` 在驗證設置時如何辨認物件的參數。它會印出物件的參數清單，包含參數名、型別、預設值、參數說明、和參數原生地。

- 當物件參數有 `**kwargs`，且在內部以 `**kwargs` 展開作為其他物件的參數時，TwinConf 能辨認出其他物件的參數也屬於該物件的參數
    - Given: 物件定義
        ```python
        # ./definition.py
        class Parent:
            def __init__(self, a: int, b: str, c: bool = True):
                """
                Args:
                    a: 蘋果
                    b: 香蕉
                    c: 車子
                """

        class Child(Parent):
            def __init__(self, d: float, **kwargs):
                """
                Args:
                    d: 鴨子
                """
                super().__init__(3, b=d + 4, **kwargs)
        ```
    - When: 給定物件路徑 `twinhelp definition.Child`
    - Then: TwinConf 會 import 該物件，並印出該物件的參數
        ```
        For `definition.Child`:
            d(float): 鴨子
        For `definition.Parent`:
            c(bool, default=True): 車子
        ```
        - 不包含參數 a, b ，因為它們在 Child 裡面被手動設值了
        - 包含參數 c ，因為它有預設值，且 Child 裡面沒有手動設值
        - 不包含參數 self 不會出現在列表中

- 不限於 class 間，也適用於 function, instance method, or class method，和這四種的任意組合。
    - Given:
        ```python
        # ./objects.py
        class BClass:
            def my_method(self, *args, f: float): 
                """
                Args:
                    f(int): 狐狸
                """

        class AClass:
            @classmethod
            def create(cls, e, **kwargs) -> "AClass":
                b = BClass()
                b.my_method(5, **kwargs)

        class MyClass:
            def __init__(self, a, b: bool, c, **kwargs):
                AClass.create(**kwargs)

        def func(d, **kwargs):
            MyClass(3, c = d * 5, **kwargs)
        ```
    - When: 給定物件路徑 `twinhelp objects.func`
    - Then: 印出
        ```
        For `objects.func`:
            d
        For `objects.MyClass`:
            b(bool)
        For `objects.AClass`:
            e
        For `objects.BClass`:
            f(float): 狐狸
        ```
        此例中可辨認出 `func` 的參數為 d, b, e, f。沒有 a, c 是因為其已在 `func` 裡面被手動設值。沒有 cls 和 self 是因為不包含物件本身。

- 若在函式主體中 `**kwargs` 被使用多次，則只追蹤第一次展開的物件的參數
- 若是用在多重繼承的親類別初始化中，則僅會追蹤第一順位的親類別

## Configuration Object

### Access & Manipulation

- dict style:
    - 取值：`config['model']['learning_rate']`
    - 預設值：`config['model'].get('learning_rate', 0.01)`
    - 設值：`config['model']['learning_rate'] = 0.01`
    - 刪除：`config['model'].pop('learning_rate')`
- attribute style:
    - 取值：`config.model.learning_rate`
    - 預設值：`getattr(config.model, 'learning_rate', 0.01)`
    - 設值：`config.model.learning_rate = 0.01`
    - 刪除：`delattr(config.model, 'learning_rate')`

### Serialization

- `kwargs`: 若值對應到物件，則會回傳除了 `TYPE` 以外的參數值字典
    - Given: 設置 `config` 等同於
        ```yaml
        model:
            TYPE: AwesomeModel
            hidden_size: 64
        ```
    - When: `config.model.kwargs`
    - Then: 回傳的字典應該是 `{'hidden_size': 64}`。方便直接將參數傳給物件初始化
        ```python
        model = config.model.TYPE(**config.model.kwargs)
        ```

- `pretty`: 為方便記錄美觀，回傳字典，其對 nested key flatten，且可以排除指定的 key，同時把物件值換成其類別名稱。
    - Given: 設置 `config` 等同於
        ```python
        {
            'model': {
                'TYPE': AwesomeModel,
                'hidden_size': 64
            },
            'dataset': {
                'batch_size': 32
            }
        }
        ```
    - When: `config.pretty()`
    - Then: 回傳的字典應該是
        ```python
        {
            "model.TYPE": "AwesomeModel",
            "model.hidden_size": 64,
            "dataset.batch_size": 32
        }
        ```
    - When:  `config.pretty(exclude=['dataset.batch_size'])`
    - Then: 回傳的字典應該是
        ```python
        {
            "model.TYPE": "AwesomeModel",
            "model.hidden_size": 64
        }
        ```

### Resolve object

- 遞迴由深至淺地，將任何帶有 `TYPE` 的設置值轉成物件實例或函式返回值

    - Given: 設置 `config` 等同於
        ```yaml
        model:
            TYPE: AwesomeModel
            hidden_size: 64
            optimizer: 
                TYPE: create_optimizer
                lr: 0.01
        ```
    - And: 物件定義
        ```python
        class Optimizer:
            def __init__(self, lr): ...

        class AwesomeModel:
            def __init__(self, hidden_size, optimizer: Optimizer): ...
        
        def create_optimizer(lr) -> Optimizer: ...
        ```
    - When: `resolved_config = config.resolve_object()`
    - Then: 得到的 `resolved_config` 等同於
        ```python
        {
            'model': AwesomeModel(
                hidden_size=64, 
                optimizer=create_optimizer(lr=0.01),
            )
        }
        ```

- 若想要在解析物件時，手動傳入參數覆蓋原參數，可以
    - When: 呼叫 `resolve_object` 時指定欲覆蓋的參數的 nested key 和值
        ```python
        model: AwesomeModel = config.model.resolve_object(overwrites={'optimizer.lr': 0.02})
        ```
    - Then: 得到 `AwesomeModel` 實例，如同
        ```python
        model = AwesomeModel(
            hidden_size=64,
            optimizer=create_optimizer(lr=0.02),
        )

- 若不想要初始化子物件，則不要在該子物件處使用 `TYPE` 標籤，可以使用 pyyaml built-in tag 指定類別。例如
    ```yaml
    model:
        class: AwesomeModel
        hidden_size: 64
        optimizer: 
            creator: !!python/name:<module_path>.create_optimizer
            lr: 0.001
    ```
    在初始化 `AwesomeModel` 時，會將 `config.model.optimizer` 以原始形式代入`optimizer` 參數

## List manipulation

TwinConf 提供 `LIST` 為一個特殊的 `TYPE` 值，來以 dict 的方式修改 list 的元素

- Given: 設置
    ```yaml
    # configs/default.yaml
    callbacks:
        TYPE: LIST
        log: log_callback
        ckpt: save_model_callback
    ```
    ```yaml
    # config.yaml
    callbacks:
        MERGE: default.callbacks
        ckpt: DELETE
        stop: early_stopping_callback
    ```
- When: 設定設置庫為 `configs` 的 `TwinConfParser` 讀取 `config.yaml`
- Then: 得到設置如同
    ```yaml
    callbacks:
        - log_callback
        - early_stopping_callback
    ```
    利用了 dict-style 方式來修改，但最後還是得到了 list

## Sweep over values

若想要在保持設置建構邏輯的情況下，得到不同參數組合的設置，可以在程式中使用迴圈，並在每次迴圈中呼叫 `parse_args`，並在命令列參數中覆蓋想要改變的參數

- Give: 有做某些 interpolation 的設置檔
    ```yaml
    dataset: imagenet
    devices: [1, 2]
    batch_size_per_device: ${`batch_size`//len(`devices`)}
    ```
- When:  
    ```python
    parser = TwinConfParser()
    for dataset in ['iris', 'cifar10']:
        for batch_size in [32, 64]:
            if dataset == 'iris' and batch_size == 32:
                continue
            config = parser.parse_args(sys.argv[1:] + [f"--dataset={dataset}", f"--batch_size={batch_size}"])
    ```
- Then: 每個 loop 依序得到 `config` 如同
    ```yaml
    dataset: iris
    devices: [1, 2]
    batch_size_per_device: 16
    batch_size: 32
    ```
    ```yaml
    dataset: cifar10
    devices: [1, 2]
    batch_size_per_device: 16
    batch_size: 32
    ```
    ```yaml
    dataset: cifar10
    devices: [1, 2]
    batch_size_per_device: 32
    batch_size: 64
    ```
