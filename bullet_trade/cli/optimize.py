"""
参数优化命令处理

运行参数优化
"""

import json
from pathlib import Path


def run_optimize(args):
    """
    运行参数优化
    
    Args:
        args: 命令行参数
        
    Returns:
        退出码
    """
    print("=" * 60)
    print("BulletTrade - 参数优化")
    print("=" * 60)
    print()
    
    # 验证文件
    strategy_file = Path(args.strategy_file)
    params_file = Path(args.params)
    
    if not strategy_file.exists():
        print(f"❌ 策略文件不存在: {strategy_file}")
        return 1
    
    if not params_file.exists():
        print(f"❌ 参数文件不存在: {params_file}")
        return 1
    
    # 读取参数配置
    try:
        with open(params_file, 'r', encoding='utf-8') as f:
            param_config = json.load(f)
    except Exception as e:
        print(f"❌ 读取参数文件失败: {e}")
        return 1
    
    # 提取参数网格
    param_grid = param_config.get('param_grid', {})
    if not param_grid:
        print("❌ 参数文件中未找到 'param_grid' 配置")
        return 1
    
    print(f"策略文件: {strategy_file}")
    print(f"参数文件: {params_file}")
    print(f"回测区间: {args.start} 至 {args.end}")
    print(f"并行进程: {args.processes or '自动'}")
    print(f"\n参数网格:")
    for key, values in param_grid.items():
        print(f"  {key}: {values}")
    print()
    
    try:
        # 导入优化器
        from bullet_trade.core.optimizer import run_param_grid
        
        # 运行优化
        print("开始参数优化...")
        results_df = run_param_grid(
            strategy_file=str(strategy_file),
            start_date=args.start,
            end_date=args.end,
            param_grid=param_grid,
            processes=args.processes,
            output_csv=args.output
        )
        
        # 显示最优参数
        print("\n" + "=" * 60)
        print("优化完成！")
        print("=" * 60)
        print(f"\n结果已保存至: {args.output}")
        print(f"\n前5名参数组合:")
        print(results_df.head().to_string())
        print("=" * 60)
        
        return 0
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("\n提示: 请确保已正确安装 BulletTrade")
        return 1
        
    except Exception as e:
        print(f"❌ 优化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

